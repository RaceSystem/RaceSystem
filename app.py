import os, threading, uuid, shutil, logging, json, sqlite3, traceback, time
from datetime import datetime
from flask import Flask, request, jsonify, Response, send_file, send_from_directory, stream_with_context,send_from_directory
import os, json
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# 從環境變數讀取 Service Account JSON
service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
service_account_credentials = None
if service_account_json:
    with open("/tmp/service_account.json", "w") as f:
        f.write(service_account_json)
    gauth = GoogleAuth()
    gauth.LoadServiceConfig()  # 使用默認設定
    gauth.ServiceAuth(settings_file="/tmp/service_account.json")  # 透過 JSON 認證
    drive = GoogleDrive(gauth)
else:
    raise ValueError("環境變數 GOOGLE_SERVICE_ACCOUNT_JSON 未設置")

def upload_to_drive(local_path, folder_id):
    """上傳檔案到指定資料夾"""
    f = drive.CreateFile({'parents':[{'id': folder_id}], 'title': os.path.basename(local_path)})
    f.SetContentFile(local_path)
    f.Upload()
    return f['id'], f['alternateLink']


logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger("race")

BASE_DIR = r"/content/final_project"
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
RESULT_FOLDER = os.path.join(BASE_DIR, "results")
STATIC_FOLDER = os.path.join(BASE_DIR, "static")
DB_FILE = os.path.join(BASE_DIR, "race.db")

for d in [UPLOAD_FOLDER, RESULT_FOLDER, STATIC_FOLDER]:
    os.makedirs(d, exist_ok=True)

# ===== SQLite helpers =====
def sqlite_execute(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(query, params)
    if fetch:
        rows = c.fetchall()
        conn.commit()
        conn.close()
        return rows
    conn.commit()
    conn.close()

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS participants (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT,
                 photo_path TEXT,
                 age INTEGER,
                 created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                 id TEXT PRIMARY KEY,
                 type TEXT,
                 payload TEXT,
                 status TEXT,
                 message TEXT,
                 result_json TEXT,
                 created_at TEXT,
                 updated_at TEXT)''')
    conn.commit()
    conn.close()

init_db()

def safe_filename_with_uuid(fname):
    from werkzeug.utils import secure_filename
    return f"{uuid.uuid4().hex}__{secure_filename(fname)}"

def enqueue_task(task_id, task_type, payload):
    now = datetime.now().isoformat()
    sqlite_execute("INSERT INTO tasks (id,type,payload,status,message,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
                   (task_id, task_type, json.dumps(payload), "queued", "", now, now))

def update_task_status(task_id, status, message="", result_json=None):
    now = datetime.now().isoformat()
    sqlite_execute("UPDATE tasks SET status=?, message=?, result_json=?, updated_at=? WHERE id=?",
                   (status, message, json.dumps(result_json) if result_json else None, now, task_id))

# ==== utility: save results locally per-date ====
def save_results_locally(src_paths, project_name="race"):
    today = datetime.now().strftime("%Y-%m-%d")
    date_folder = os.path.join(RESULT_FOLDER, today)
    os.makedirs(date_folder, exist_ok=True)
    saved_paths = []
    for p in src_paths:
        if not os.path.exists(p):
            continue
        ext = os.path.splitext(p)[1]
        base = f"{project_name}-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}{ext}"
        dest = os.path.join(date_folder, base)
        shutil.copy(p, dest)
        saved_paths.append(dest)
    return saved_paths

# ===== MultiViewProcessor with strict face-first matching + per-person tracker =====
class MultiViewProcessor:
    def __init__(self, video_paths, orig_filenames, finish_line_y=None, race_size=8, fps=None, offsets=None, face_tol=0.45):
        self.video_paths = video_paths
        self.orig_filenames = orig_filenames
        self.finish_line_y = finish_line_y
        self.race_size = int(race_size)
        self.fps = fps
        self.offsets = offsets or [0,0,0]
        self.face_tol = face_tol
        self.task_id = None
        self._yolo = None
        self._face_encs = []  # [(pid,name,enc)]
        self._cv2 = None

    def lazy_load(self):
        if self._yolo is None:
            try:
                from ultralytics import YOLO
                self._yolo = YOLO('yolov8n.pt')
            except Exception as e:
                logger.error("YOLO load error: %s", e)
                raise
        if not self._face_encs:
            import face_recognition
            import numpy as np
            rows = sqlite_execute("SELECT id,name,photo_path FROM participants WHERE COALESCE(photo_path,'')!=''", fetch=True)
            encs = []
            for pid, name, photo_path in rows:
                local_p = os.path.join(UPLOAD_FOLDER, os.path.basename(photo_path))
                if os.path.exists(local_p):
                    try:
                        img = face_recognition.load_image_file(local_p)
                        fencs = face_recognition.face_encodings(img)
                        if fencs:
                            encs.append((pid, name, fencs[0]))
                    except Exception as e:
                        logger.warning("Failed to encode participant %s: %s", name, e)
            self._face_encs = encs

    def detect_people(self, frame):
        self.lazy_load()
        try:
            results = self._yolo.predict(frame, imgsz=640, conf=0.35, verbose=False)
        except Exception as e:
            logger.error("YOLO prediction failed: %s", e)
            return []
        bboxes = []
        if not results: return bboxes
        r = results[0]
        for b in getattr(r, "boxes", []):
            xyxy = b.xyxy.cpu().numpy().tolist()[0] if hasattr(b, "xyxy") else None
            if xyxy:
                x1,y1,x2,y2 = [int(x) for x in xyxy]
                bboxes.append([x1,y1,x2,y2])
        return bboxes

    def match_face_in_bbox(self, frame, bbox):
        try:
            import face_recognition, numpy as np
        except Exception as e:
            logger.warning("face_recognition import failed: %s", e)
            return None
        x1, y1, x2, y2 = bbox
        h, w = frame.shape[:2]
        padx = int((x2 - x1) * 0.1)
        pady = int((y2 - y1) * 0.15)
        ax1 = max(0, x1 + padx)
        ay1 = max(0, y1 + pady)
        ax2 = min(w, x2 - padx)
        ay2 = min(h, y2 - pady)
        crop = frame[ay1:ay2, ax1:ax2]
        if crop.size == 0:
            return None
        rgb = crop[:, :, ::-1]
        try:
            encs = face_recognition.face_encodings(rgb)
        except Exception as e:
            logger.warning("face_encodings failed: %s", e)
            return None
        if not encs:
            return None
        enc = encs[0]
        best = None
        bestd = 1.0
        for pid, name, p_enc in self._face_encs:
            try:
                d = np.linalg.norm(p_enc - enc)
            except Exception:
                try:
                    d = face_recognition.face_distance([p_enc], enc)[0]
                except:
                    d = 1.0
            if d < bestd:
                bestd = d
                best = (pid, name, d)
        if best and best[2] <= self.face_tol:
            return {'participant_id': best[0], 'participant_name': best[1], 'distance': best[2]}
        return None

    def process(self):
        import cv2, numpy as np
        self.lazy_load()
        results_summary = []

        for idx, video_path in enumerate(self.video_paths):
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.warning("Cannot open video: %s", video_path)
                continue
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 360
            fps = cap.get(cv2.CAP_PROP_FPS) or (self.fps or 25.0)
            finish_line_y = self.finish_line_y or int(height * 0.92)
            out_name = f"{uuid.uuid4().hex}_annotated.mp4"
            out_path = os.path.join(RESULT_FOLDER, out_name)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out_writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

            frame_idx = 0
            discovered = {}
            finish_times = []

            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_idx += 1

                # Update trackers
                to_remove = []
                for tkey, tinfo in list(discovered.items()):
                    tr = tinfo.get('tracker')
                    if tr:
                        ok, tb = tr.update(frame)
                        if not ok:
                            to_remove.append(tkey)
                            continue
                        x,y,wid,hei = [int(v) for v in tb]
                        x1,y1,x2,y2 = x, y, x+wid, y+hei
                        cv2.rectangle(frame, (x1,y1), (x2,y2), (0,200,0), 2)
                        cv2.putText(frame, f"{tinfo['participant_name']}", (x1, max(0,y1-6)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
                        if y2 >= finish_line_y:
                            if not any(ft['participant']==tinfo['participant_name'] for ft in finish_times):
                                finish_times.append({'participant': tinfo['participant_name'], 'finish_time': round(frame_idx/fps, 2)})
                for k in to_remove:
                    discovered.pop(k, None)

                run_detect = (frame_idx % 6 == 0) or (len(discovered) == 0)
                if run_detect:
                    bboxes = self.detect_people(frame)
                    for box in bboxes:
                        x1,y1,x2,y2 = box
                        skip = False
                        for tinfo in discovered.values():
                            last = tinfo.get('last_bbox')
                            if last:
                                lx1,ly1,lx2,ly2 = last
                                ix1 = max(lx1, x1); iy1 = max(ly1, y1)
                                ix2 = min(lx2, x2); iy2 = min(ly2, y2)
                                if ix2>ix1 and iy2>iy1:
                                    skip = True; break
                        if skip: continue
                        fm = self.match_face_in_bbox(frame, box)
                        if fm:
                            tracker = cv2.TrackerCSRT_create()
                            bbox_xywh = (x1, y1, x2-x1, y2-y1)
                            try:
                                tracker.init(frame, bbox_xywh)
                                tkey = uuid.uuid4().hex
                                discovered[tkey] = {'participant_id': fm['participant_id'],
                                                    'participant_name': fm['participant_name'],
                                                    'tracker': tracker,
                                                    'last_bbox': [x1,y1,x2,y2],
                                                    'first_frame': frame_idx}
                                logger.info("Started tracking %s (pid=%s) on frame %d", fm['participant_name'], fm['participant_id'], frame_idx)
                            except Exception as e:
                                logger.warning("Tracker init failed: %s", e)
                cv2.line(frame, (0, finish_line_y), (width, finish_line_y), (0,0,255), 2)
                out_writer.write(frame)

            cap.release()
            out_writer.release()

            # Sort finish times
            finish_times.sort(key=lambda x: x['finish_time'])
            results_summary.append({'video': os.path.basename(video_path),
                                    'out_video': out_name,
                                    'rankings': finish_times})

            # Save permanently in date-folder
            try:
                saved_paths = save_results_locally([video_path, out_path])
                logger.info("Saved outputs locally: %s", saved_paths)
            except Exception as e:
                logger.warning("Failed to save outputs locally: %s", e)

        return results_summary

# ===== Flask app & endpoints =====
app = Flask(__name__, static_folder=STATIC_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 1024*1024*1024  # 1GB

@app.route('/')
def index():
    return send_file(r"C:\race_project\index.html")

@app.route('/add_participant', methods=['POST'])
def add_participant():
    name = request.form.get("name", "").strip()
    age = request.form.get("age", None)
    photo = request.files.get("photo")
    if not name or not photo:
        return jsonify({"error": "缺少姓名或照片"}), 400
    saved_fname = safe_filename_with_uuid(photo.filename)
    local_photo_path = os.path.join(UPLOAD_FOLDER, saved_fname)
    photo.save(local_photo_path)
    sqlite_execute("INSERT INTO participants (name, photo_path, age, created_at) VALUES (?,?,?,?)",
                   (name, saved_fname, int(age) if age and age.isdigit() else None, datetime.now().isoformat()))
    return jsonify({"message": f"參賽者 {name} 建立成功", "photo_url": saved_fname})

# 上傳多視角影片
@app.route('/upload_multi', methods=['POST'])
def upload_multi():
    try:
        v1 = request.files.get('video1')
        v2 = request.files.get('video2')
        v3 = request.files.get('video3')
        if not (v1 and v2 and v3):
            return jsonify({'error': '請上傳 video1、video2、video3'}), 400
        saved = []
        orig_names = []
        for f in [v1, v2, v3]:
            fname = safe_filename_with_uuid(f.filename)
            localp = os.path.join(UPLOAD_FOLDER, fname)
            f.save(localp)
            saved.append(localp)
            orig_names.append(f.filename)
        task_id = uuid.uuid4().hex
        payload = {'videos': saved, 'orig': orig_names}
        enqueue_task(task_id, 'process_multi', payload)
        def bg():
            def bg():
                update_task_status(task_id, 'processing', 'started multi-view processing')
                try:
                    proc = MultiViewProcessor(saved, orig_names)
                    proc.task_id = task_id
                    res = proc.process()

                    # 取得最終存檔路徑
                    final_paths = []
                    for r in res:
                        out_video = r['out_video']
                        # 查找日期資料夾
                        for d in os.listdir(RESULT_FOLDER):
                            dpath = os.path.join(RESULT_FOLDER, d)
                            fpath = os.path.join(dpath, out_video)
                        if os.path.exists(fpath):
                            final_paths.append(fpath)
                            break

                # 更新任務狀態
                    update_task_status(task_id, 'done', 'processed successfully', {'summary': res, 'local_paths': final_paths})
                except Exception as e:
                    logger.exception('Processing failed')
                    update_task_status(task_id, 'error', str(e))

        threading.Thread(target=bg, daemon=True).start()
        return jsonify({'task_id': task_id, 'status': 'queued'})
    except Exception as e:
        logger.exception("upload_multi handler error")
        return jsonify({'error': 'server error', 'detail': str(e)}), 500

@app.route('/task_status/<task_id>')
def task_status(task_id):
    rows = sqlite_execute("SELECT status,message,result_json FROM tasks WHERE id=?", (task_id,), fetch=True)
    if not rows:
        return jsonify({'error': 'task not found'}), 404
    status, message, result_json = rows[0]
    return jsonify({'status': status, 'message': message, 'result': json.loads(result_json) if result_json else None})

# Range-supporting streaming for result files
def parse_range(range_header, file_size):
    if not range_header:
        return None
    try:
        units, rng = range_header.split("=", 1)
        if units.strip() != "bytes":
            return None
        start_s, end_s = rng.split("-", 1)
        start = int(start_s) if start_s else 0
        end = int(end_s) if end_s else file_size - 1
        if start > end:
            return None
        return start, end
    except:
        return None

@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json')

@app.route('/service-worker.js')
def service_worker():
    return send_from_directory('.', 'service-worker.js')

@app.route('/results/<path:filename>')
def results_file(filename):
    path = None
    # try find in date-folders
    for d in os.listdir(RESULT_FOLDER):
        dpath = os.path.join(RESULT_FOLDER, d)
        fpath = os.path.join(dpath, filename)
        if os.path.exists(fpath):
            path = fpath
            break
    if not path:
        return "Not found", 404
    file_size = os.path.getsize(path)
    range_header = request.headers.get('Range', None)
    rng = parse_range(range_header, file_size)
    def generate(start, end, path):
        with open(path, 'rb') as f:
            f.seek(start)
            left = end - start + 1
            chunk_size = 1024*1024
            while left > 0:
                read_len = min(chunk_size, left)
                data = f.read(read_len)
                if not data:
                    break
                yield data
                left -= len(data)
    if rng:
        start, end = rng
        resp = Response(stream_with_context(generate(start, end, path)), status=206, mimetype='video/mp4')
        resp.headers.add('Content-Range', f'bytes {start}-{end}/{file_size}')
        resp.headers.add('Accept-Ranges', 'bytes')
        resp.headers.add('Content-Length', str(end-start+1))
        return resp
    else:
        return send_from_directory(os.path.dirname(path), os.path.basename(path), as_attachment=False)

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 5000))
    pp.run(host="0.0.0.0", port=PORT)
