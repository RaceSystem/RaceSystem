import os, threading, uuid, json, logging
from datetime import datetime
from flask import Flask, request, jsonify
from supabase import create_client
import boto3

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger("race")

# ====== Supabase 初始化 ======
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ====== Cloudflare R2 初始化 ======
R2_KEY_ID = os.environ.get("R2_KEY_ID")
R2_SECRET_KEY = os.environ.get("R2_SECRET_KEY")
R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
R2_BUCKET = os.environ.get("R2_BUCKET")

s3_client = boto3.client(
    "s3",
    region_name="auto",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_KEY_ID,
    aws_secret_access_key=R2_SECRET_KEY,
)

# ====== 本地資料夾 ======
BASE_DIR = "/tmp/final_project"
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
RESULT_FOLDER = os.path.join(BASE_DIR, "results")
STATIC_FOLDER = os.path.join(BASE_DIR, "static")
for d in [UPLOAD_FOLDER, RESULT_FOLDER, STATIC_FOLDER]:
    os.makedirs(d, exist_ok=True)

# ===== Helper =====
def upload_to_r2(local_path, remote_name):
    s3_client.upload_file(local_path, R2_BUCKET, remote_name)
    return f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com/{R2_BUCKET}/{remote_name}"

def safe_filename_with_uuid(fname):
    from werkzeug.utils import secure_filename
    return f"{uuid.uuid4().hex}__{secure_filename(fname)}"

def add_participant_to_db(name, age, photo_url):
    supabase_client.table("participants").insert({
        "name": name,
        "age": age,
        "photo_url": photo_url,
        "created_at": datetime.utcnow().isoformat()
    }).execute()

def enqueue_task(task_id, task_type, payload):
    supabase_client.table("tasks").insert({
        "id": task_id,
        "type": task_type,
        "payload": json.dumps(payload),
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }).execute()

def update_task_status(task_id, status, message="", result_json=None):
    supabase_client.table("tasks").update({
        "status": status,
        "message": message,
        "result_json": json.dumps(result_json) if result_json else None,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", task_id).execute()

# ===== Flask App =====
app = Flask(__name__, static_folder=STATIC_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 1024*1024*1024  # 1GB

@app.route('/add_participant', methods=['POST'])
def add_participant():
    name = request.form.get("name", "").strip()
    age = request.form.get("age", None)
    photo = request.files.get("photo")
    if not name or not photo:
        return jsonify({"error": "缺少姓名或照片"}), 400

    saved_fname = safe_filename_with_uuid(photo.filename)
    local_path = os.path.join(UPLOAD_FOLDER, saved_fname)
    photo.save(local_path)
    r2_url = upload_to_r2(local_path, saved_fname)

    add_participant_to_db(name, int(age) if age and age.isdigit() else None, r2_url)
    return jsonify({"message": f"參賽者 {name} 建立成功", "photo_url": r2_url})

@app.route('/upload_multi', methods=['POST'])
def upload_multi():
    try:
        files = [request.files.get(f'video{i}') for i in range(1,4)]
        if any(f is None for f in files):
            return jsonify({'error': '請上傳 video1、video2、video3'}), 400

        saved_paths, orig_names, r2_urls = [], [], []
        for f in files:
            fname = safe_filename_with_uuid(f.filename)
            local_path = os.path.join(UPLOAD_FOLDER, fname)
            f.save(local_path)
            saved_paths.append(local_path)
            orig_names.append(f.filename)
            r2_urls.append(upload_to_r2(local_path, fname))

        task_id = uuid.uuid4().hex
        enqueue_task(task_id, "process_multi", {"videos": r2_urls, "orig": orig_names})

        def bg():
            update_task_status(task_id, 'processing', 'started multi-view processing')
            try:
                from processor import MultiViewProcessor
                proc = MultiViewProcessor(saved_paths, orig_names)
                proc.task_id = task_id
                res = proc.process()

                final_paths = []
                for r in res:
                    out_video = r['out_video']
                    out_local_path = os.path.join(RESULT_FOLDER, out_video)
                    if os.path.exists(out_local_path):
                        url = upload_to_r2(out_local_path, out_video)
                        final_paths.append(url)

                update_task_status(task_id, 'done', 'processed successfully', {'summary': res, 'r2_urls': final_paths})
            except Exception as e:
                logger.exception("Processing failed")
                update_task_status(task_id, 'error', str(e))

        threading.Thread(target=bg, daemon=True).start()
        return jsonify({'task_id': task_id, 'status': 'queued'})
    except Exception as e:
        logger.exception("upload_multi error")
        return jsonify({'error': 'server error', 'detail': str(e)}), 500

@app.route('/task_status/<task_id>')
def task_status(task_id):
    res = supabase_client.table("tasks").select("*").eq("id", task_id).execute()
    if not res.data or len(res.data) == 0:
        return jsonify({'error': 'task not found'}), 404
    row = res.data[0]
    return jsonify({
        "status": row['status'],
        "message": row['message'],
        "result": json.loads(row['result_json']) if row['result_json'] else None
    })

@app.route('/results/<path:filename>')
def results_file(filename):
    return jsonify({"url": f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com/{R2_BUCKET}/{filename}"})

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=PORT)
