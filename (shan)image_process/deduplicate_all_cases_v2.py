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

OUTPUT_IMAGE_HASH_CSV = WORK_DIR / "all_jpg_hashes_v2_private.csv"
OUTPUT_CASE_SUMMARY_CSV = WORK_DIR / "jpg_case_summary_v2_private.csv"
OUTPUT_DUPLICATE_IMAGE_CSV = WORK_DIR / "duplicate_images_v2_private.csv"
OUTPUT_DUPLICATE_EXPORT_CSV = WORK_DIR / "duplicate_export_candidates_private.csv"


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tif",
    ".tiff",
}


def get_batch_dirs():
    return sorted([
        p for p in ROOT_DIR.iterdir()
        if p.is_dir() and p.name.startswith("Temp")
    ])


def find_jpg_roots(batch_dir):
    roots = []

    for path in batch_dir.rglob("JPG"):

        if (
            path.is_dir()
            and path.parent.name == "IHE_PDI"
        ):
            roots.append(path)

    return roots


def calculate_sha256(file_path):
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:

        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


def get_export_id(jpg_root, batch_dir):
    """
    嘗試從 JPG root 找出 export 資料夾名稱。

    例如：
    Temp_260716_1
      /20260716_151644_2742
      /IHE_PDI
      /JPG

    ExportID = 20260716_151644_2742

    如果是：
    Temp_DX_xxx
      /20260716_xxx
      /IHE_PDI
      /JPG

    一樣可抓上一層 export。
    """

    try:
        relative = jpg_root.relative_to(batch_dir)

        parts = relative.parts

        # ... / ExportID / IHE_PDI / JPG
        if len(parts) >= 3:
            return parts[-3]

        # 如果 JPG 幾乎直接在 batch 下
        return batch_dir.name

    except Exception:
        return batch_dir.name


def scan_all_images():

    records = []
    total_images = 0

    print("=" * 90)
    print("JPG 跨批次去重掃描 V2")
    print("唯一鍵：Batch + ExportID + FolderID")
    print("只讀原始影像，不會修改任何資料")
    print("=" * 90)
    print()

    for batch_dir in get_batch_dirs():

        batch_name = batch_dir.name

        print(f"掃描：{batch_name}")

        jpg_roots = find_jpg_roots(batch_dir)

        print(
            f"找到 JPG root：{len(jpg_roots)}"
        )

        for jpg_root in jpg_roots:

            export_id = get_export_id(
                jpg_root,
                batch_dir
            )

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

                        "ExportID":
                            export_id,

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

    print(
        f"影像總數：{total_images}"
    )
    print()

    return records


def build_case_summary(records):
    """
    原始病例 instance：

    Batch + ExportID + FolderID
    """

    case_map = {}

    for row in records:

        key = (
            row["Batch"],
            row["ExportID"],
            row["FolderID"],
        )

        if key not in case_map:

            case_map[key] = {
                "Batch":
                    row["Batch"],

                "ExportID":
                    row["ExportID"],

                "FolderID":
                    row["FolderID"],

                "ImageCount":
                    0,

                "Hashes":
                    [],
            }

        item = case_map[key]

        item["ImageCount"] += 1
        item["Hashes"].append(
            row["SHA256"]
        )

    result = []

    for item in case_map.values():

        sorted_hashes = sorted(
            item["Hashes"]
        )

        combined = "|".join(
            sorted_hashes
        )

        fingerprint = hashlib.sha256(
            combined.encode("utf-8")
        ).hexdigest()

        result.append({
            "Batch":
                item["Batch"],

            "ExportID":
                item["ExportID"],

            "FolderID":
                item["FolderID"],

            "ImageCount":
                item["ImageCount"],

            "CaseFingerprint":
                fingerprint,

            "ImageHashes":
                " | ".join(
                    sorted_hashes
                ),
        })

    return result


def find_duplicate_images(records):

    hash_map = defaultdict(list)

    for row in records:
        hash_map[row["SHA256"]].append(row)

    duplicates = []
    group_index = 0

    for sha256, rows in hash_map.items():

        if len(rows) <= 1:
            continue

        group_index += 1

        for row in rows:

            duplicates.append({
                "DuplicateImageGroup":
                    f"IMG_DUP_{group_index:04d}",

                "SHA256":
                    sha256,

                "Batch":
                    row["Batch"],

                "ExportID":
                    row["ExportID"],

                "FolderID":
                    row["FolderID"],

                "FileName":
                    row["FileName"],

                "FullPath":
                    row["FullPath"],
            })

    return duplicates


def find_duplicate_exports(case_summary):
    """
    CaseFingerprint 完全相同
    = 整組 JPG 內容完全相同。

    這是 duplicate export 強候選。
    """

    fingerprint_map = defaultdict(list)

    for row in case_summary:

        fingerprint_map[
            row["CaseFingerprint"]
        ].append(row)

    duplicates = []
    group_index = 0

    for fingerprint, rows in fingerprint_map.items():

        if len(rows) <= 1:
            continue

        group_index += 1

        for row in rows:

            duplicates.append({
                "DuplicateExportGroup":
                    f"EXPORT_DUP_{group_index:04d}",

                "CaseFingerprint":
                    fingerprint,

                "Batch":
                    row["Batch"],

                "ExportID":
                    row["ExportID"],

                "FolderID":
                    row["FolderID"],

                "ImageCount":
                    row["ImageCount"],

                "ReviewStatus":
                    "EXACT_IMAGE_SET_MATCH",
            })

    return duplicates


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

    duplicate_exports = find_duplicate_exports(
        case_summary
    )

    save_csv(
        OUTPUT_IMAGE_HASH_CSV,
        records,
        [
            "Batch",
            "ExportID",
            "FolderID",
            "JPGRoot",
            "FileName",
            "FileSizeBytes",
            "SHA256",
            "FullPath",
        ]
    )

    save_csv(
        OUTPUT_CASE_SUMMARY_CSV,
        case_summary,
        [
            "Batch",
            "ExportID",
            "FolderID",
            "ImageCount",
            "CaseFingerprint",
            "ImageHashes",
        ]
    )

    save_csv(
        OUTPUT_DUPLICATE_IMAGE_CSV,
        duplicate_images,
        [
            "DuplicateImageGroup",
            "SHA256",
            "Batch",
            "ExportID",
            "FolderID",
            "FileName",
            "FullPath",
        ]
    )

    save_csv(
        OUTPUT_DUPLICATE_EXPORT_CSV,
        duplicate_exports,
        [
            "DuplicateExportGroup",
            "CaseFingerprint",
            "Batch",
            "ExportID",
            "FolderID",
            "ImageCount",
            "ReviewStatus",
        ]
    )

    unique_hashes = len({
        row["SHA256"]
        for row in records
    })

    duplicate_image_groups = len({
        row["DuplicateImageGroup"]
        for row in duplicate_images
    })

    duplicate_export_groups = len({
        row["DuplicateExportGroup"]
        for row in duplicate_exports
    })

    print("=" * 90)
    print("V2 掃描完成")
    print("=" * 90)

    print(
        f"JPG 影像總數：{len(records)}"
    )

    print(
        f"唯一影像 SHA256：{unique_hashes}"
    )

    print(
        f"原始病例 instance 數：{len(case_summary)}"
    )

    print(
        f"完全相同影像群組數："
        f"{duplicate_image_groups}"
    )

    print(
        f"完全相同病例匯出群組數："
        f"{duplicate_export_groups}"
    )

    print()
    print("病例 summary：")
    print(OUTPUT_CASE_SUMMARY_CSV)

    print()
    print("完全相同病例匯出候選：")
    print(OUTPUT_DUPLICATE_EXPORT_CSV)

    print()
    print("原始資料沒有被修改。")


if __name__ == "__main__":
    main()