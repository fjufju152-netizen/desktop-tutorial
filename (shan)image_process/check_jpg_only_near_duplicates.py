from pathlib import Path
import csv
from itertools import combinations

from PIL import Image
import imagehash


# =========================================================
# 工作資料夾
# =========================================================

WORK_DIR = Path(
    r"C:\Users\Administrator\Desktop\fjuh-機密資料勿外流 Don't disclose confidential Information"
    r"\shan_process_work"
)

GLOBAL_MASTER_PRIVATE = WORK_DIR / "global_case_master_private.csv"
ALL_JPG_HASHES_PRIVATE = WORK_DIR / "all_jpg_hashes_v2_private.csv"

OUTPUT_CSV = WORK_DIR / "jpg_only_near_duplicate_candidates_private.csv"


# =========================================================
# pHash 距離門檻
#
# 0      = 完全相同 perceptual hash
# 1~4    = 非常相似
# 5~8    = 可能相似，建議人工檢查
# > 8    = 通常先不列入
# =========================================================

PHASH_THRESHOLD = 8


def normalize(value):
    if value is None:
        return ""
    return str(value).strip()


# =========================================================
# 讀 JPG-only cases
# =========================================================

def load_jpg_only_cases():

    cases = {}

    with open(
        GLOBAL_MASTER_PRIVATE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            if normalize(row["CaseStatus"]) != "JPG_ONLY":
                continue

            key = (
                normalize(row["Batch"]),
                normalize(row["ExportID"]),
                normalize(row["FolderID"]),
            )

            cases[key] = {
                "GlobalAnonID":
                    normalize(row["GlobalAnonID"]),

                "Batch":
                    key[0],

                "ExportID":
                    key[1],

                "FolderID":
                    key[2],
            }

    return cases


# =========================================================
# 找 JPG-only 對應影像
# =========================================================

def load_jpg_only_images(jpg_only_cases):

    images = []

    with open(
        ALL_JPG_HASHES_PRIVATE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            key = (
                normalize(row["Batch"]),
                normalize(row["ExportID"]),
                normalize(row["FolderID"]),
            )

            case = jpg_only_cases.get(key)

            if case is None:
                continue

            images.append({
                "GlobalAnonID":
                    case["GlobalAnonID"],

                "Batch":
                    case["Batch"],

                "ExportID":
                    case["ExportID"],

                "FolderID":
                    case["FolderID"],

                "FileName":
                    normalize(row["FileName"]),

                "SHA256":
                    normalize(row["SHA256"]),

                "FullPath":
                    normalize(row["FullPath"]),
            })

    return images


# =========================================================
# pHash
# =========================================================

def calculate_phash(image_path):

    try:

        with Image.open(image_path) as img:

            # 轉灰階比較適合 X 光影像
            img = img.convert("L")

            return imagehash.phash(
                img,
                hash_size=16
            )

    except Exception as e:

        print(
            f"[WARNING] 無法計算 pHash：{image_path}"
        )
        print(
            f"原因：{type(e).__name__}: {e}"
        )

        return None


# =========================================================
# 計算所有 JPG-only pHash
# =========================================================

def calculate_all_phashes(images):

    print("=" * 90)
    print("計算 JPG-only 影像 pHash")
    print("=" * 90)
    print()

    total = len(images)

    for index, item in enumerate(
        images,
        start=1
    ):

        item["pHash"] = calculate_phash(
            item["FullPath"]
        )

        if index % 50 == 0:
            print(
                f"已處理 {index}/{total} 張"
            )

    valid = [
        item
        for item in images
        if item["pHash"] is not None
    ]

    print()
    print(
        f"成功計算 pHash：{len(valid)}"
    )

    print(
        f"失敗：{total - len(valid)}"
    )

    print()

    return valid


# =========================================================
# 找近似影像
# =========================================================

def find_candidates(images):

    candidates = []

    pair_count = 0

    print("=" * 90)
    print("開始比較 JPG-only 影像")
    print("=" * 90)
    print()

    for image_a, image_b in combinations(
        images,
        2
    ):

        # -------------------------------------------------
        # 同一病例裡自己的不同影像不用互相比
        # -------------------------------------------------

        if (
            image_a["GlobalAnonID"]
            == image_b["GlobalAnonID"]
        ):
            continue

        pair_count += 1

        distance = (
            image_a["pHash"]
            - image_b["pHash"]
        )

        if distance > PHASH_THRESHOLD:
            continue

        same_sha256 = (
            image_a["SHA256"]
            == image_b["SHA256"]
        )

        same_folder_id = (
            image_a["FolderID"]
            == image_b["FolderID"]
        )

        same_batch = (
            image_a["Batch"]
            == image_b["Batch"]
        )

        if same_sha256:

            review_status = (
                "EXACT_DUPLICATE_IMAGE"
            )

        elif distance <= 2:

            review_status = (
                "VERY_HIGH_SIMILARITY"
            )

        elif distance <= 4:

            review_status = (
                "HIGH_SIMILARITY"
            )

        else:

            review_status = (
                "POSSIBLE_SIMILARITY"
            )

        candidates.append({
            "CaseA":
                image_a["GlobalAnonID"],

            "CaseB":
                image_b["GlobalAnonID"],

            "BatchA":
                image_a["Batch"],

            "BatchB":
                image_b["Batch"],

            "ExportIDA":
                image_a["ExportID"],

            "ExportIDB":
                image_b["ExportID"],

            "FolderIDA":
                image_a["FolderID"],

            "FolderIDB":
                image_b["FolderID"],

            "ImageA":
                image_a["FileName"],

            "ImageB":
                image_b["FileName"],

            "pHashDistance":
                distance,

            "SameSHA256":
                same_sha256,

            "SameFolderID":
                same_folder_id,

            "SameBatch":
                same_batch,

            "ReviewStatus":
                review_status,

            "PathA":
                image_a["FullPath"],

            "PathB":
                image_b["FullPath"],
        })

    candidates.sort(
        key=lambda x: (
            int(x["pHashDistance"]),
            x["CaseA"],
            x["CaseB"],
        )
    )

    print(
        f"實際比較 pair 數：{pair_count}"
    )

    print(
        f"pHash <= {PHASH_THRESHOLD} 候選："
        f"{len(candidates)}"
    )

    print()

    return candidates


# =========================================================
# CSV
# =========================================================

def save_candidates(candidates):

    fields = [
        "CaseA",
        "CaseB",
        "BatchA",
        "BatchB",
        "ExportIDA",
        "ExportIDB",
        "FolderIDA",
        "FolderIDB",
        "ImageA",
        "ImageB",
        "pHashDistance",
        "SameSHA256",
        "SameFolderID",
        "SameBatch",
        "ReviewStatus",
        "PathA",
        "PathB",
    ]

    with open(
        OUTPUT_CSV,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()
        writer.writerows(
            candidates
        )


def main():

    print("=" * 90)
    print("JPG-only 近似影像去重候選")
    print("本程式只讀取影像，不會修改任何原始資料")
    print("=" * 90)
    print()

    jpg_only_cases = load_jpg_only_cases()

    print(
        f"JPG-only case 數："
        f"{len(jpg_only_cases)}"
    )

    images = load_jpg_only_images(
        jpg_only_cases
    )

    print(
        f"JPG-only 影像數："
        f"{len(images)}"
    )

    print()

    images = calculate_all_phashes(
        images
    )

    candidates = find_candidates(
        images
    )

    save_candidates(
        candidates
    )

    exact_count = sum(
        1
        for row in candidates
        if row["ReviewStatus"]
        == "EXACT_DUPLICATE_IMAGE"
    )

    very_high_count = sum(
        1
        for row in candidates
        if row["ReviewStatus"]
        == "VERY_HIGH_SIMILARITY"
    )

    high_count = sum(
        1
        for row in candidates
        if row["ReviewStatus"]
        == "HIGH_SIMILARITY"
    )

    possible_count = sum(
        1
        for row in candidates
        if row["ReviewStatus"]
        == "POSSIBLE_SIMILARITY"
    )

    print("=" * 90)
    print("完成")
    print("=" * 90)

    print(
        f"EXACT_DUPLICATE_IMAGE："
        f"{exact_count}"
    )

    print(
        f"VERY_HIGH_SIMILARITY："
        f"{very_high_count}"
    )

    print(
        f"HIGH_SIMILARITY："
        f"{high_count}"
    )

    print(
        f"POSSIBLE_SIMILARITY："
        f"{possible_count}"
    )

    print()
    print("候選清單：")
    print(OUTPUT_CSV)

    print()
    print(
        "注意：本程式只產生候選，"
        "不會自動合併或刪除病例。"
    )


if __name__ == "__main__":
    main()