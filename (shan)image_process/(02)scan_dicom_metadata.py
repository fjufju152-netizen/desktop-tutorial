from pathlib import Path
import csv
import pydicom


# =========================================================
# 原始 DICOM 根目錄
# 只讀，不修改、不刪除、不搬移
# =========================================================

DCM_ROOT = Path(
    r"C:\Users\Administrator\Desktop\fjuh-機密資料勿外流 Don't disclose confidential Information"
    r"\Temp_DX_260708-260611_200筆"
    r"\20260716_161501_2742"
    r"\IMAGE"
    r"\DCM"
)

# =========================================================
# 輸出資料夾
# =========================================================

OUTPUT_DIR = Path(
    r"C:\Users\Administrator\Desktop\fjuh-機密資料勿外流 Don't disclose confidential Information"
    r"\shan_process_work"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = OUTPUT_DIR / "dicom_metadata.csv"
SUMMARY_CSV = OUTPUT_DIR / "dicom_patient_summary.csv"


def safe_get(ds, field_name):
    """
    安全讀取 DICOM metadata 欄位。
    如果不存在就回傳空字串。
    """
    value = getattr(ds, field_name, "")

    if value is None:
        return ""

    return str(value)


def scan_dicom_files(root_dir):
    """
    遞迴掃描整個 DCM_ROOT。
    只讀 DICOM header，不讀 pixel data。
    """

    print("=" * 80)
    print("DICOM Metadata 掃描")
    print("本程式只讀取 metadata，不會修改原始資料")
    print("=" * 80)
    print()

    print("掃描位置：")
    print(root_dir)
    print()

    if not root_dir.exists():
        print("[ERROR] 找不到 DCM_ROOT")
        return []

    all_files = [
        p for p in root_dir.rglob("*")
        if p.is_file()
    ]

    print(f"總檔案數：{len(all_files)}")
    print()

    records = []

    dicom_count = 0
    non_dicom_count = 0
    error_count = 0

    for i, file_path in enumerate(all_files, start=1):

        try:
            ds = pydicom.dcmread(
                file_path,
                stop_before_pixels=True,
                force=True
            )

            # 至少要有 SOPInstanceUID，才比較像真正 DICOM instance
            sop_uid = safe_get(ds, "SOPInstanceUID")

            if not sop_uid:
                non_dicom_count += 1
                continue

            dicom_count += 1

            relative_path = file_path.relative_to(root_dir)

            # 取相對路徑第一層，方便觀察原始 DCM 分組
            top_folder = (
                relative_path.parts[0]
                if len(relative_path.parts) > 1
                else ""
            )

            record = {
                "TopFolder": top_folder,
                "RelativePath": str(relative_path),

                "PatientID": safe_get(ds, "PatientID"),
                "PatientName": safe_get(ds, "PatientName"),

                "StudyInstanceUID": safe_get(
                    ds,
                    "StudyInstanceUID"
                ),

                "SeriesInstanceUID": safe_get(
                    ds,
                    "SeriesInstanceUID"
                ),

                "SOPInstanceUID": sop_uid,

                "StudyDate": safe_get(
                    ds,
                    "StudyDate"
                ),

                "StudyTime": safe_get(
                    ds,
                    "StudyTime"
                ),

                "Modality": safe_get(
                    ds,
                    "Modality"
                ),

                "BodyPartExamined": safe_get(
                    ds,
                    "BodyPartExamined"
                ),

                "ViewPosition": safe_get(
                    ds,
                    "ViewPosition"
                ),

                "StudyDescription": safe_get(
                    ds,
                    "StudyDescription"
                ),

                "SeriesDescription": safe_get(
                    ds,
                    "SeriesDescription"
                ),

                "AccessionNumber": safe_get(
                    ds,
                    "AccessionNumber"
                ),

                "Laterality": safe_get(
                    ds,
                    "Laterality"
                ),

                "ImageLaterality": safe_get(
                    ds,
                    "ImageLaterality"
                ),

                "Rows": safe_get(
                    ds,
                    "Rows"
                ),

                "Columns": safe_get(
                    ds,
                    "Columns"
                ),

                "BitsAllocated": safe_get(
                    ds,
                    "BitsAllocated"
                ),

                "BitsStored": safe_get(
                    ds,
                    "BitsStored"
                ),

                "PhotometricInterpretation": safe_get(
                    ds,
                    "PhotometricInterpretation"
                ),

                "Manufacturer": safe_get(
                    ds,
                    "Manufacturer"
                ),

                "FileName": file_path.name,
                "FullPath": str(file_path),
            }

            records.append(record)

            if dicom_count % 50 == 0:
                print(
                    f"已找到 {dicom_count} 個 DICOM instance"
                )

        except Exception as e:
            error_count += 1

            if error_count <= 10:
                print(
                    f"[WARNING] 讀取失敗：{file_path}"
                )
                print(
                    f"原因：{type(e).__name__}: {e}"
                )
                print()

    print()
    print("=" * 80)
    print("掃描完成")
    print("=" * 80)
    print(f"DICOM instance：{dicom_count}")
    print(f"非 DICOM / 無 SOP UID：{non_dicom_count}")
    print(f"讀取失敗：{error_count}")
    print()

    return records


def save_metadata_csv(records):
    if not records:
        print("沒有可輸出的 DICOM metadata。")
        return

    fieldnames = [
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

        "BitsAllocated",
        "BitsStored",

        "PhotometricInterpretation",

        "Manufacturer",

        "FileName",
        "FullPath",
    ]

    with open(
        OUTPUT_CSV,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(records)

    print("已輸出：")
    print(OUTPUT_CSV)
    print()


def save_patient_summary(records):
    """
    按 PatientID 彙整。
    這份仍屬於敏感資料，不要上傳 GitHub。
    """

    patient_map = {}

    for row in records:
        patient_id = row["PatientID"]

        # 有些 DICOM 可能 PatientID 是空白
        if not patient_id:
            patient_id = "[EMPTY_PATIENT_ID]"

        if patient_id not in patient_map:
            patient_map[patient_id] = {
                "PatientID": patient_id,
                "InstanceCount": 0,
                "StudyUIDs": set(),
                "SeriesUIDs": set(),
                "TopFolders": set(),
                "BodyParts": set(),
                "ViewPositions": set(),
                "Modalities": set(),
            }

        item = patient_map[patient_id]

        item["InstanceCount"] += 1

        if row["StudyInstanceUID"]:
            item["StudyUIDs"].add(
                row["StudyInstanceUID"]
            )

        if row["SeriesInstanceUID"]:
            item["SeriesUIDs"].add(
                row["SeriesInstanceUID"]
            )

        if row["TopFolder"]:
            item["TopFolders"].add(
                row["TopFolder"]
            )

        if row["BodyPartExamined"]:
            item["BodyParts"].add(
                row["BodyPartExamined"]
            )

        if row["ViewPosition"]:
            item["ViewPositions"].add(
                row["ViewPosition"]
            )

        if row["Modality"]:
            item["Modalities"].add(
                row["Modality"]
            )

    summary_records = []

    for patient_id, item in sorted(
        patient_map.items(),
        key=lambda x: x[0]
    ):
        summary_records.append({
            "PatientID": patient_id,
            "InstanceCount": item["InstanceCount"],
            "StudyCount": len(item["StudyUIDs"]),
            "SeriesCount": len(item["SeriesUIDs"]),
            "TopFolderCount": len(item["TopFolders"]),

            "TopFolders": " | ".join(
                sorted(item["TopFolders"])
            ),

            "BodyParts": " | ".join(
                sorted(item["BodyParts"])
            ),

            "ViewPositions": " | ".join(
                sorted(item["ViewPositions"])
            ),

            "Modalities": " | ".join(
                sorted(item["Modalities"])
            ),
        })

    with open(
        SUMMARY_CSV,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "PatientID",
                "InstanceCount",
                "StudyCount",
                "SeriesCount",
                "TopFolderCount",
                "TopFolders",
                "BodyParts",
                "ViewPositions",
                "Modalities",
            ]
        )

        writer.writeheader()
        writer.writerows(summary_records)

    print("已輸出：")
    print(SUMMARY_CSV)
    print()

    print(f"DICOM 中不同 PatientID 數量：{len(summary_records)}")

    empty_exists = any(
        row["PatientID"] == "[EMPTY_PATIENT_ID]"
        for row in summary_records
    )

    if empty_exists:
        print(
            "[WARNING] 有 DICOM 的 PatientID 是空白。"
        )


def main():

    records = scan_dicom_files(DCM_ROOT)

    if not records:
        return

    save_metadata_csv(records)
    save_patient_summary(records)

    print()
    print("=" * 80)
    print("第二階段完成")
    print("原始資料沒有被修改。")
    print("=" * 80)


if __name__ == "__main__":
    main()