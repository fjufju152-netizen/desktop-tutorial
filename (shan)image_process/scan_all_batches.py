from pathlib import Path
import csv
import pydicom


# =========================================================
# 根目錄
# =========================================================

ROOT_DIR = Path(
    r"C:\Users\Administrator\Desktop\fjuh-機密資料勿外流 Don't disclose confidential Information"
)

# 只掃 Temp 開頭的資料夾
BATCH_DIRS = sorted([
    p for p in ROOT_DIR.iterdir()
    if p.is_dir() and p.name.startswith("Temp")
])

# =========================================================
# 輸出位置
# =========================================================

OUTPUT_DIR = ROOT_DIR / "shan_process_work"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BATCH_SUMMARY_CSV = OUTPUT_DIR / "batch_summary.csv"
ALL_DICOM_METADATA_CSV = OUTPUT_DIR / "all_dicom_metadata.csv"
ALL_PATIENT_SUMMARY_CSV = OUTPUT_DIR / "all_patient_summary_private.csv"


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tif",
    ".tiff",
}


def safe_get(ds, field_name):
    value = getattr(ds, field_name, "")

    if value is None:
        return ""

    return str(value)


def find_jpg_roots(batch_dir):
    """
    找出 batch 裡所有 IHE_PDI/JPG。
    不假設一定只有一個。
    """
    results = []

    for path in batch_dir.rglob("JPG"):
        if path.is_dir() and path.parent.name == "IHE_PDI":
            results.append(path)

    return results


def find_dcm_roots(batch_dir):
    """
    找出 batch 裡所有 IMAGE/DCM。
    """
    results = []

    for path in batch_dir.rglob("DCM"):
        if path.is_dir() and path.parent.name == "IMAGE":
            results.append(path)

    return results


def count_jpg_images(jpg_roots):
    total_images = 0
    case_folders = set()

    for root in jpg_roots:
        for folder in root.iterdir():

            if not folder.is_dir():
                continue

            case_key = str(folder.relative_to(ROOT_DIR))
            case_folders.add(case_key)

            for file in folder.rglob("*"):

                if (
                    file.is_file()
                    and file.suffix.lower() in IMAGE_EXTENSIONS
                ):
                    total_images += 1

    return len(case_folders), total_images


def scan_dicom_roots(batch_name, dcm_roots):
    records = []

    all_files_count = 0
    dicom_count = 0
    non_dicom_count = 0
    error_count = 0

    for dcm_root in dcm_roots:

        for file_path in dcm_root.rglob("*"):

            if not file_path.is_file():
                continue

            all_files_count += 1

            try:
                ds = pydicom.dcmread(
                    file_path,
                    stop_before_pixels=True,
                    force=True
                )

                sop_uid = safe_get(ds, "SOPInstanceUID")

                if not sop_uid:
                    non_dicom_count += 1
                    continue

                dicom_count += 1

                relative_to_dcm = file_path.relative_to(dcm_root)

                top_folder = (
                    relative_to_dcm.parts[0]
                    if len(relative_to_dcm.parts) > 1
                    else ""
                )

                records.append({
                    "Batch": batch_name,
                    "DCMRoot": str(dcm_root),
                    "TopFolder": top_folder,
                    "RelativePath": str(relative_to_dcm),

                    "PatientID": safe_get(ds, "PatientID"),
                    "PatientName": safe_get(ds, "PatientName"),

                    "StudyInstanceUID":
                        safe_get(ds, "StudyInstanceUID"),

                    "SeriesInstanceUID":
                        safe_get(ds, "SeriesInstanceUID"),

                    "SOPInstanceUID":
                        sop_uid,

                    "StudyDate":
                        safe_get(ds, "StudyDate"),

                    "StudyTime":
                        safe_get(ds, "StudyTime"),

                    "Modality":
                        safe_get(ds, "Modality"),

                    "BodyPartExamined":
                        safe_get(ds, "BodyPartExamined"),

                    "ViewPosition":
                        safe_get(ds, "ViewPosition"),

                    "StudyDescription":
                        safe_get(ds, "StudyDescription"),

                    "SeriesDescription":
                        safe_get(ds, "SeriesDescription"),

                    "AccessionNumber":
                        safe_get(ds, "AccessionNumber"),

                    "Laterality":
                        safe_get(ds, "Laterality"),

                    "ImageLaterality":
                        safe_get(ds, "ImageLaterality"),

                    "Rows":
                        safe_get(ds, "Rows"),

                    "Columns":
                        safe_get(ds, "Columns"),

                    "FileName":
                        file_path.name,

                    "FullPath":
                        str(file_path),
                })

            except Exception:
                error_count += 1

    return {
        "records": records,
        "all_files_count": all_files_count,
        "dicom_count": dicom_count,
        "non_dicom_count": non_dicom_count,
        "error_count": error_count,
    }


def build_patient_summary(all_dicom_records):
    patient_map = {}

    for row in all_dicom_records:

        batch = row["Batch"]
        patient_id = row["PatientID"].strip()

        if not patient_id:
            patient_id = "[EMPTY_PATIENT_ID]"

        key = (batch, patient_id)

        if key not in patient_map:

            patient_map[key] = {
                "Batch": batch,
                "PatientID": patient_id,
                "InstanceCount": 0,
                "StudyUIDs": set(),
                "SeriesUIDs": set(),
                "TopFolders": set(),
                "BodyParts": set(),
                "ViewPositions": set(),
                "Modalities": set(),
                "DXCount": 0,
                "SRCount": 0,
                "OtherCount": 0,
            }

        item = patient_map[key]

        item["InstanceCount"] += 1

        study_uid = row["StudyInstanceUID"]
        if study_uid:
            item["StudyUIDs"].add(study_uid)

        series_uid = row["SeriesInstanceUID"]
        if series_uid:
            item["SeriesUIDs"].add(series_uid)

        top_folder = row["TopFolder"]
        if top_folder:
            item["TopFolders"].add(top_folder)

        body_part = row["BodyPartExamined"]
        if body_part:
            item["BodyParts"].add(body_part)

        view = row["ViewPosition"]
        if view:
            item["ViewPositions"].add(view)

        modality = row["Modality"]
        if modality:

            item["Modalities"].add(modality)

            if modality == "DX":
                item["DXCount"] += 1

            elif modality == "SR":
                item["SRCount"] += 1

            else:
                item["OtherCount"] += 1

    summary = []

    for item in patient_map.values():

        summary.append({
            "Batch":
                item["Batch"],

            "PatientID":
                item["PatientID"],

            "InstanceCount":
                item["InstanceCount"],

            "StudyCount":
                len(item["StudyUIDs"]),

            "SeriesCount":
                len(item["SeriesUIDs"]),

            "TopFolderCount":
                len(item["TopFolders"]),

            "TopFolders":
                " | ".join(
                    sorted(item["TopFolders"])
                ),

            "BodyParts":
                " | ".join(
                    sorted(item["BodyParts"])
                ),

            "ViewPositions":
                " | ".join(
                    sorted(item["ViewPositions"])
                ),

            "Modalities":
                " | ".join(
                    sorted(item["Modalities"])
                ),

            "DXCount":
                item["DXCount"],

            "SRCount":
                item["SRCount"],

            "OtherModalityCount":
                item["OtherCount"],
        })

    return summary


def save_csv(path, rows, fieldnames):

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(rows)


def main():

    print("=" * 90)
    print("全批次資料盤點")
    print("只讀取原始資料，不會修改任何原始影像")
    print("=" * 90)
    print()

    print(f"找到 Temp 批次數：{len(BATCH_DIRS)}")

    for batch in BATCH_DIRS:
        print(" -", batch.name)

    print()

    batch_summary = []
    all_dicom_records = []

    for batch_dir in BATCH_DIRS:

        batch_name = batch_dir.name

        print("=" * 90)
        print(f"掃描批次：{batch_name}")
        print("=" * 90)

        jpg_roots = find_jpg_roots(batch_dir)
        dcm_roots = find_dcm_roots(batch_dir)

        jpg_case_count, jpg_image_count = count_jpg_images(
            jpg_roots
        )

        dicom_result = scan_dicom_roots(
            batch_name,
            dcm_roots
        )

        dicom_records = dicom_result["records"]

        all_dicom_records.extend(
            dicom_records
        )

        patient_ids = {
            row["PatientID"].strip()
            for row in dicom_records
            if row["PatientID"].strip()
        }

        modalities = {
            row["Modality"].strip()
            for row in dicom_records
            if row["Modality"].strip()
        }

        body_parts = {
            row["BodyPartExamined"].strip()
            for row in dicom_records
            if row["BodyPartExamined"].strip()
        }

        dx_count = sum(
            1
            for row in dicom_records
            if row["Modality"] == "DX"
        )

        sr_count = sum(
            1
            for row in dicom_records
            if row["Modality"] == "SR"
        )

        other_count = sum(
            1
            for row in dicom_records
            if row["Modality"]
            not in {"", "DX", "SR"}
        )

        batch_summary.append({
            "Batch":
                batch_name,

            "JPGRootCount":
                len(jpg_roots),

            "DCMRootCount":
                len(dcm_roots),

            "JPGCaseFolderCount":
                jpg_case_count,

            "JPGImageCount":
                jpg_image_count,

            "DICOMFileCount":
                dicom_result["dicom_count"],

            "DICOMPatientCount":
                len(patient_ids),

            "DXCount":
                dx_count,

            "SRCount":
                sr_count,

            "OtherModalityCount":
                other_count,

            "Modalities":
                " | ".join(
                    sorted(modalities)
                ),

            "BodyParts":
                " | ".join(
                    sorted(body_parts)
                ),

            "NonDicomCount":
                dicom_result["non_dicom_count"],

            "ReadErrorCount":
                dicom_result["error_count"],
        })

        print(f"JPG root：{len(jpg_roots)}")
        print(f"DCM root：{len(dcm_roots)}")
        print(f"JPG 病例資料夾：{jpg_case_count}")
        print(f"JPG 影像總數：{jpg_image_count}")
        print(f"DICOM instance：{dicom_result['dicom_count']}")
        print(f"DICOM PatientID：{len(patient_ids)}")
        print(f"DX：{dx_count}")
        print(f"SR：{sr_count}")
        print(
            "BodyPart：",
            " | ".join(sorted(body_parts))
            if body_parts
            else "(空)"
        )
        print()

    patient_summary = build_patient_summary(
        all_dicom_records
    )

    save_csv(
        BATCH_SUMMARY_CSV,
        batch_summary,
        [
            "Batch",
            "JPGRootCount",
            "DCMRootCount",
            "JPGCaseFolderCount",
            "JPGImageCount",
            "DICOMFileCount",
            "DICOMPatientCount",
            "DXCount",
            "SRCount",
            "OtherModalityCount",
            "Modalities",
            "BodyParts",
            "NonDicomCount",
            "ReadErrorCount",
        ]
    )

    save_csv(
        ALL_DICOM_METADATA_CSV,
        all_dicom_records,
        [
            "Batch",
            "DCMRoot",
            "TopFolder",
            "RelativePath",
            "PatientID",
            "PatientName",
            "StudyInstanceUID",
            "SeriesInstanceUID",
            "SOPInstanceUID",
            "StudyDate",
            "StudyTime",
            "Modality",
            "BodyPartExamined",
            "ViewPosition",
            "StudyDescription",
            "SeriesDescription",
            "AccessionNumber",
            "Laterality",
            "ImageLaterality",
            "Rows",
            "Columns",
            "FileName",
            "FullPath",
        ]
    )

    save_csv(
        ALL_PATIENT_SUMMARY_CSV,
        patient_summary,
        [
            "Batch",
            "PatientID",
            "InstanceCount",
            "StudyCount",
            "SeriesCount",
            "TopFolderCount",
            "TopFolders",
            "BodyParts",
            "ViewPositions",
            "Modalities",
            "DXCount",
            "SRCount",
            "OtherModalityCount",
        ]
    )

    print("=" * 90)
    print("全部批次掃描完成")
    print("=" * 90)

    print()
    print("批次統計：")
    print(BATCH_SUMMARY_CSV)

    print()
    print("全部 DICOM metadata：")
    print(ALL_DICOM_METADATA_CSV)

    print()
    print("全部病人 DICOM summary：")
    print(ALL_PATIENT_SUMMARY_CSV)

    print()
    print("原始資料沒有被修改。")


if __name__ == "__main__":
    main()