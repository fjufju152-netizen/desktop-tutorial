from pathlib import Path
import csv
import shutil
from collections import defaultdict


# =========================================================
# 工作資料夾
# =========================================================

WORK_DIR = Path(
    r"C:\Users\Administrator\Desktop\fjuh-機密資料勿外流 Don't disclose confidential Information"
    r"\shan_process_work"
)

GLOBAL_MASTER = WORK_DIR / "global_case_master_private.csv"
ALL_JPG_HASHES = WORK_DIR / "all_jpg_hashes_v2_private.csv"
DUPLICATE_EXPORTS = WORK_DIR / "duplicate_export_candidates_private.csv"


# =========================================================
# YOLO 最終工作資料夾
# =========================================================

YOLO_ROOT = WORK_DIR / "final_yolo_dataset"

IMAGES_DIR = YOLO_ROOT / "images_all"
LABELS_DIR = YOLO_ROOT / "labels_all"

PUBLIC_INDEX = YOLO_ROOT / "image_index.csv"
PRIVATE_MAPPING = YOLO_ROOT / "private_image_mapping.csv"


def normalize(value):
    if value is None:
        return ""
    return str(value).strip()


# =========================================================
# 建立資料夾
# =========================================================

def prepare_directories():

    IMAGES_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    LABELS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


# =========================================================
# 讀 Global Case Master
# =========================================================

def load_global_cases():

    cases = {}

    with open(
        GLOBAL_MASTER,
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

            cases[key] = {
                "GlobalAnonID":
                    normalize(row["GlobalAnonID"]),

                "Batch":
                    key[0],

                "ExportID":
                    key[1],

                "FolderID":
                    key[2],

                "DICOMPatientID":
                    normalize(row["DICOMPatientID"]),

                "CaseStatus":
                    normalize(row["CaseStatus"]),

                "DuplicateExportGroup":
                    normalize(row["DuplicateExportGroup"]),
            }

    return cases


# =========================================================
# 找出 duplicate export
#
# 每一組只保留排序後第一個 export
# =========================================================

def build_duplicate_keep_map():

    duplicate_groups = defaultdict(list)

    if not DUPLICATE_EXPORTS.exists():
        return {}

    with open(
        DUPLICATE_EXPORTS,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            group = normalize(
                row["DuplicateExportGroup"]
            )

            key = (
                normalize(row["Batch"]),
                normalize(row["ExportID"]),
                normalize(row["FolderID"]),
            )

            duplicate_groups[group].append(
                key
            )

    keep_map = {}

    for group, keys in duplicate_groups.items():

        sorted_keys = sorted(keys)

        keep_key = sorted_keys[0]

        for key in sorted_keys:

            keep_map[key] = (
                key == keep_key
            )

    return keep_map


# =========================================================
# 讀所有 JPG
# =========================================================

def load_all_jpg_images():

    images = []

    with open(
        ALL_JPG_HASHES,
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

            images.append({
                "CaseKey":
                    key,

                "Batch":
                    key[0],

                "ExportID":
                    key[1],

                "FolderID":
                    key[2],

                "OriginalFileName":
                    normalize(row["FileName"]),

                "SHA256":
                    normalize(row["SHA256"]),

                "OriginalPath":
                    normalize(row["FullPath"]),
            })

    return images


# =========================================================
# 篩選要保留的 case
# =========================================================

def should_keep_case(case_key, duplicate_keep_map):

    # 不在 duplicate group 中
    if case_key not in duplicate_keep_map:
        return True

    # duplicate group 中只保留一份
    return duplicate_keep_map[case_key]


# =========================================================
# 複製匿名影像
# =========================================================

def copy_images(
    cases,
    all_images,
    duplicate_keep_map
):

    # GlobalAnonID -> image list
    patient_images = defaultdict(list)

    skipped_duplicate_exports = 0
    unmatched_images = 0

    for image in all_images:

        case_key = image["CaseKey"]

        case = cases.get(case_key)

        if case is None:

            unmatched_images += 1
            continue

        if not should_keep_case(
            case_key,
            duplicate_keep_map
        ):

            skipped_duplicate_exports += 1
            continue

        patient_images[
            case["GlobalAnonID"]
        ].append({
            **image,
            **case,
        })

    public_records = []
    private_records = []

    copied_count = 0

    # =====================================================
    # 同一病人的所有影像一起排序
    # =====================================================

    for global_id in sorted(
        patient_images.keys()
    ):

        images = patient_images[
            global_id
        ]

        images = sorted(
            images,
            key=lambda x: (
                x["Batch"],
                x["ExportID"],
                x["FolderID"],
                x["OriginalFileName"],
            )
        )

        # ---------------------------------------------
        # 同一病人內再用 SHA256 去一次重複
        #
        # 防止同病人不同 export 有單張重複，
        # 但整個 case 並非完整 duplicate。
        # ---------------------------------------------

        seen_hashes = set()
        unique_images = []

        for image in images:

            sha = image["SHA256"]

            if sha in seen_hashes:
                continue

            seen_hashes.add(sha)
            unique_images.append(image)

        for image_index, image in enumerate(
            unique_images,
            start=1
        ):

            source = Path(
                image["OriginalPath"]
            )

            extension = (
                source.suffix.lower()
                if source.suffix
                else ".jpg"
            )

            new_name = (
                f"{global_id}_"
                f"{image_index:02d}"
                f"{extension}"
            )

            destination = (
                IMAGES_DIR / new_name
            )

            # =============================================
            # 只複製
            # 不修改、不移動原始資料
            # =============================================

            shutil.copy2(
                source,
                destination
            )

            copied_count += 1

            # =============================================
            # 一般索引
            # 不放原始病例資訊
            # =============================================

            public_records.append({
                "GlobalAnonID":
                    global_id,

                "ImageName":
                    new_name,

                "ImageIndex":
                    image_index,

                "CaseStatus":
                    image["CaseStatus"],
            })

            # =============================================
            # 私密對照
            # =============================================

            private_records.append({
                "GlobalAnonID":
                    global_id,

                "ImageName":
                    new_name,

                "ImageIndex":
                    image_index,

                "Batch":
                    image["Batch"],

                "ExportID":
                    image["ExportID"],

                "FolderID":
                    image["FolderID"],

                "DICOMPatientID":
                    image["DICOMPatientID"],

                "OriginalFileName":
                    image["OriginalFileName"],

                "SHA256":
                    image["SHA256"],

                "OriginalPath":
                    image["OriginalPath"],

                "CopiedPath":
                    str(destination),

                "CaseStatus":
                    image["CaseStatus"],
            })

    return {
        "public_records":
            public_records,

        "private_records":
            private_records,

        "copied_count":
            copied_count,

        "skipped_duplicate_exports":
            skipped_duplicate_exports,

        "unmatched_images":
            unmatched_images,

        "patient_count":
            len(patient_images),
    }


# =========================================================
# CSV
# =========================================================

def save_csv(
    path,
    rows,
    fields
):

    with open(
        path,
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
            rows
        )


# =========================================================
# main
# =========================================================

def main():

    print("=" * 90)
    print("建立最終匿名 YOLO 工作資料集")
    print("原始影像只會被讀取與複製，不會修改")
    print("=" * 90)
    print()

    prepare_directories()

    cases = load_global_cases()

    print(
        f"Global case instance："
        f"{len(cases)}"
    )

    duplicate_keep_map = (
        build_duplicate_keep_map()
    )

    duplicate_case_instances = len(
        duplicate_keep_map
    )

    print(
        f"完整重複 export instance："
        f"{duplicate_case_instances}"
    )

    all_images = load_all_jpg_images()

    print(
        f"原始 JPG 紀錄："
        f"{len(all_images)}"
    )

    print()

    result = copy_images(
        cases,
        all_images,
        duplicate_keep_map
    )

    # =====================================================
    # 一般 index
    # =====================================================

    save_csv(
        PUBLIC_INDEX,
        result["public_records"],
        [
            "GlobalAnonID",
            "ImageName",
            "ImageIndex",
            "CaseStatus",
        ]
    )

    # =====================================================
    # 私密 mapping
    # =====================================================

    save_csv(
        PRIVATE_MAPPING,
        result["private_records"],
        [
            "GlobalAnonID",
            "ImageName",
            "ImageIndex",
            "Batch",
            "ExportID",
            "FolderID",
            "DICOMPatientID",
            "OriginalFileName",
            "SHA256",
            "OriginalPath",
            "CopiedPath",
            "CaseStatus",
        ]
    )

    print("=" * 90)
    print("完成")
    print("=" * 90)

    print(
        f"最終匿名病人 ID 數："
        f"{result['patient_count']}"
    )

    print(
        f"最終複製影像數："
        f"{result['copied_count']}"
    )

    print(
        f"因完整 duplicate export "
        f"而跳過的 JPG 紀錄："
        f"{result['skipped_duplicate_exports']}"
    )

    print(
        f"無法對到 global master 的影像："
        f"{result['unmatched_images']}"
    )

    print()
    print("匿名影像：")
    print(IMAGES_DIR)

    print()
    print("CVAT labels 預留資料夾：")
    print(LABELS_DIR)

    print()
    print("一般 image index：")
    print(PUBLIC_INDEX)

    print()
    print("私密 image mapping：")
    print(PRIVATE_MAPPING)

    print()
    print(
        "原始影像沒有被修改。"
    )


if __name__ == "__main__":
    main()