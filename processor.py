import os

class MultiViewProcessor:
    def __init__(self, video_paths, orig_names):
        self.video_paths = video_paths
        self.orig_names = orig_names
        self.task_id = None

    def process(self):
        res = []
        result_dir = "/tmp/final_project/results"
        os.makedirs(result_dir, exist_ok=True)
        for i, v in enumerate(self.orig_names):
            out_video = f"processed_{v}"
            # 模擬輸出影片生成
            with open(os.path.join(result_dir, out_video), "wb") as f:
                f.write(b"dummy video content")
            res.append({"video": v, "out_video": out_video, "rankings":[]})
        return res
