from pathlib import Path
import csv
import hashlib
from collections import defaultdict


# =========================================================
# 根目錄
# =========================================================

ROOT_DIR = Path(
    r"C:\Users\Administrator\Desktop\fjuh-機密資料勿外流 Don't disclose confidential Information"
)

WORK_DIR = ROOT_DIR / "shan_process_work"

OUTPUT_IMAGE_HASH_CSV = WORK_DIR / "all_jpg_hashes_private.csv"
OUTPUT_DUPLICATE_IMAGE_CSV = WORK_DIR / "duplicate_images_private.csv"
OUTPUT_CASE_SUMMARY_CSV = WORK_DIR / "jpg_case_summary_private.csv"
OUTPUT_DUPLICATE_CASE_CSV = WORK_DIR / "duplicate_case_candidates_private.csv"


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tif",
    ".tiff",
}


# =========================================================
# 找所有 Temp 批次
# =========================================================

def get_batch_dirs():
    return sorted([
        p for p in ROOT_DIR.iterdir()
        if p.is_dir() and p.name.startswith("Temp")
    ])


# =========================================================
# 找 IHE_PDI/JPG
# =========================================================

def find_jpg_roots(batch_dir):
    roots = []

    for path in batch_dir.rglob("JPG"):

        if (
            path.is_dir()
            and path.parent.name == "IHE_PDI"
        ):
            roots.append(path)

    return roots


# =========================================================
# SHA256
# =========================================================

def calculate_sha256(file_path):
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:

        while True:

            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


# =========================================================
# 掃描 JPG
# =========================================================

def scan_all_images():

    records = []

    batch_dirs = get_batch_dirs()

    print("=" * 90)
    print("JPG 跨批次 SHA-256 去重掃描")
    print("只讀取原始影像，不會修改任何原始資料")
    print("=" * 90)
    print()

    total_images = 0

    for batch_dir in batch_dirs:

        batch_name = batch_dir.name

        print(f"掃描：{batch_name}")

        jpg_roots = find_jpg_roots(batch_dir)

        print(
            f"找到 JPG root：{len(jpg_roots)}"
        )

        for jpg_root in jpg_roots:

            for case_folder in jpg_root.iterdir():

                if not case_folder.is_dir():
                    continue

                folder_id = case_folder.name

                for image_path in case_folder.rglob("*"):

                    if not image_path.is_file():
                        continue

                    if (
                        image_path.suffix.lower()
                        not in IMAGE_EXTENSIONS
                    ):
                        continue

                    total_images += 1

                    file_hash = calculate_sha256(
                        image_path
                    )

                    records.append({
                        "Batch":
                            batch_name,

                        "FolderID":
                            folder_id,

                        "JPGRoot":
                            str(jpg_root),

                        "FileName":
                            image_path.name,

                        "FileSizeBytes":
                            image_path.stat().st_size,

                        "SHA256":
                            file_hash,

                        "FullPath":
                            str(image_path),
                    })

                    if total_images % 100 == 0:
                        print(
                            f"  已掃描 {total_images} 張影像"
                        )

        print()

    print(f"影像總數：{total_images}")
    print()

    return records


# =========================================================
# 建病例 summary
# =========================================================

def build_case_summary(records):

    case_map = {}

    for row in records:

        key = (
            row["Batch"],
            row["FolderID"]
        )

        if key not in case_map:

            case_map[key] = {
                "Batch":
                    row["Batch"],

                "FolderID":
                    row["FolderID"],

                "ImageCount":
                    0,

                "Hashes":
                    [],
            }

        case_map[key]["ImageCount"] += 1
        case_map[key]["Hashes"].append(
            row["SHA256"]
        )

    result = []

    for item in case_map.values():

        sorted_hashes = sorted(
            item["Hashes"]
        )

        # 病例級 fingerprint
        # 把此病例所有影像 hash 排序後再 hash 一次
        combined = "|".join(
            sorted_hashes
        )

        case_fingerprint = hashlib.sha256(
            combined.encode("utf-8")
        ).hexdigest()

        result.append({
            "Batch":
                item["Batch"],

            "FolderID":
                item["FolderID"],

            "ImageCount":
                item["ImageCount"],

            "CaseFingerprint":
                case_fingerprint,

            "ImageHashes":
                " | ".join(sorted_hashes),
        })

    return result


# =========================================================
# 找重複圖片
# =========================================================

def find_duplicate_images(records):

    hash_map = defaultdict(list)

    for row in records:
        hash_map[row["SHA256"]].append(row)

    duplicates = []

    duplicate_group = 0

    for file_hash, rows in hash_map.items():

        if len(rows) <= 1:
            continue

        duplicate_group += 1

        for row in rows:

            duplicates.append({
                "DuplicateGroup":
                    f"IMG_DUP_{duplicate_group:04d}",

                "SHA256":
                    file_hash,

                "Batch":
                    row["Batch"],

                "FolderID":
                    row["FolderID"],

                "FileName":
                    row["FileName"],

                "FullPath":
                    row["FullPath"],
            })

    return duplicates


# =========================================================
# 找完全相同病例
# =========================================================

def find_duplicate_cases(case_summary):

    fingerprint_map = defaultdict(list)

    for row in case_summary:

        fingerprint_map[
            row["CaseFingerprint"]
        ].append(row)

    duplicates = []

    duplicate_group = 0

    for fingerprint, rows in fingerprint_map.items():

        if len(rows) <= 1:
            continue

        duplicate_group += 1

        for row in rows:

            duplicates.append({
                "DuplicateCaseGroup":
                    f"CASE_DUP_{duplicate_group:04d}",

                "CaseFingerprint":
                    fingerprint,

                "Batch":
                    row["Batch"],

                "FolderID":
                    row["FolderID"],

                "ImageCount":
                    row["ImageCount"],
            })

    return duplicates


# =========================================================
# CSV
# =========================================================

def save_csv(path, rows, fields):

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
        writer.writerows(rows)


# =========================================================
# main
# =========================================================

def main():

    records = scan_all_images()

    if not records:
        print("沒有找到 JPG 影像。")
        return

    case_summary = build_case_summary(
        records
    )

    duplicate_images = find_duplicate_images(
        records
    )

    duplicate_cases = find_duplicate_cases(
        case_summary
    )

    # -----------------------------------------------------
    # 全圖片 hash
    # -----------------------------------------------------

    save_csv(
        OUTPUT_IMAGE_HASH_CSV,
        records,
        [
            "Batch",
            "FolderID",
            "JPGRoot",
            "FileName",
            "FileSizeBytes",
            "SHA256",
            "FullPath",
        ]
    )

    # -----------------------------------------------------
    # 重複影像
    # -----------------------------------------------------

    save_csv(
        OUTPUT_DUPLICATE_IMAGE_CSV,
        duplicate_images,
        [
            "DuplicateGroup",
            "SHA256",
            "Batch",
            "FolderID",
            "FileName",
            "FullPath",
        ]
    )

    # -----------------------------------------------------
    # 病例 summary
    # -----------------------------------------------------

    save_csv(
        OUTPUT_CASE_SUMMARY_CSV,
        case_summary,
        [
            "Batch",
            "FolderID",
            "ImageCount",
            "CaseFingerprint",
            "ImageHashes",
        ]
    )

    # -----------------------------------------------------
    # 完全重複病例
    # -----------------------------------------------------

    save_csv(
        OUTPUT_DUPLICATE_CASE_CSV,
        duplicate_cases,
        [
            "DuplicateCaseGroup",
            "CaseFingerprint",
            "Batch",
            "FolderID",
            "ImageCount",
        ]
    )

    unique_hashes = len({
        row["SHA256"]
        for row in records
    })

    duplicate_image_files = len(
        duplicate_images
    )

    duplicate_case_groups = len({
        row["DuplicateCaseGroup"]
        for row in duplicate_cases
    })

    print("=" * 90)
    print("JPG 去重掃描完成")
    print("=" * 90)

    print(
        f"JPG 影像總數：{len(records)}"
    )

    print(
        f"唯一影像 SHA256 數：{unique_hashes}"
    )

    print(
        f"出現在重複群組中的影像檔數："
        f"{duplicate_image_files}"
    )

    print(
        f"病例資料夾總數：{len(case_summary)}"
    )

    print(
        f"完全相同病例群組數："
        f"{duplicate_case_groups}"
    )

    print()
    print("全部影像 hash：")
    print(OUTPUT_IMAGE_HASH_CSV)

    print()
    print("重複圖片：")
    print(OUTPUT_DUPLICATE_IMAGE_CSV)

    print()
    print("病例 summary：")
    print(OUTPUT_CASE_SUMMARY_CSV)

    print()
    print("完全相同病例候選：")
    print(OUTPUT_DUPLICATE_CASE_CSV)

    print()
    print("原始資料沒有被修改。")


if __name__ == "__main__":
    main()