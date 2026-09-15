from pathlib import Path
import csv
from collections import defaultdict


# =========================================================
# 工作資料夾
# =========================================================

WORK_DIR = Path(
    r"C:\Users\Administrator\Desktop\fjuh-機密資料勿外流 Don't disclose confidential Information"
    r"\shan_process_work"
)

JPG_CASE_CSV = WORK_DIR / "jpg_case_summary_v2_private.csv"
DICOM_METADATA_CSV = WORK_DIR / "all_dicom_metadata.csv"
DUPLICATE_EXPORT_CSV = WORK_DIR / "duplicate_export_candidates_private.csv"

PRIVATE_OUTPUT = WORK_DIR / "global_case_master_private.csv"
PUBLIC_OUTPUT = WORK_DIR / "global_case_master.csv"


# =========================================================
# 工具
# =========================================================

def safe_int(value):
    try:
        return int(value)
    except Exception:
        return 0


def normalize(value):
    if value is None:
        return ""
    return str(value).strip()


# =========================================================
# 讀 JPG case instance
# =========================================================

def load_jpg_cases():

    cases = {}

    with open(
        JPG_CASE_CSV,
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
                "Batch": key[0],
                "ExportID": key[1],
                "FolderID": key[2],

                "JPGCount":
                    safe_int(row["ImageCount"]),

                "CaseFingerprint":
                    normalize(row["CaseFingerprint"]),

                "PatientIDs":
                    set(),

                "DXCount":
                    0,

                "SRCount":
                    0,

                "OtherModalityCount":
                    0,

                "BodyParts":
                    set(),

                "Modalities":
                    set(),

                "StudyUIDs":
                    set(),

                "SeriesUIDs":
                    set(),

                "DuplicateExportGroup":
                    "",

                "DuplicateExportStatus":
                    "",
            }

    return cases


# =========================================================
# 從 DICOM root 推 ExportID
# =========================================================

def extract_export_id(dcm_root, batch_name):

    path = Path(dcm_root)

    try:
        # ...\Batch\ExportID\IMAGE\DCM
        # DCM parent = IMAGE
        # IMAGE parent = ExportID
        export_id = path.parent.parent.name

        # 大型 batch 有時直接：
        # Batch\IMAGE\DCM
        # 此時 export_id 會等於 Batch 名稱
        if export_id == batch_name:
            return batch_name

        return export_id

    except Exception:
        return batch_name


# =========================================================
# DICOM metadata 合併到 JPG case
# =========================================================

def merge_dicom(cases):

    unmatched_dicom = []

    with open(
        DICOM_METADATA_CSV,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            batch = normalize(row["Batch"])
            folder_id = normalize(row["TopFolder"])

            dcm_root = normalize(row["DCMRoot"])

            export_id = extract_export_id(
                dcm_root,
                batch
            )

            # 第一種：精確配對
            key = (
                batch,
                export_id,
                folder_id
            )

            item = cases.get(key)

            # 第二種：
            # 某些大型 batch 只有一個 JPG root / DCM root
            # ExportID 可能不是同一字串
            if item is None:

                candidates = [
                    value
                    for case_key, value in cases.items()
                    if (
                        case_key[0] == batch
                        and case_key[2] == folder_id
                    )
                ]

                if len(candidates) == 1:
                    item = candidates[0]

            if item is None:

                unmatched_dicom.append({
                    "Batch": batch,
                    "ExportID": export_id,
                    "FolderID": folder_id,
                    "PatientID":
                        normalize(row["PatientID"]),
                })

                continue

            patient_id = normalize(
                row["PatientID"]
            )

            if patient_id:
                item["PatientIDs"].add(
                    patient_id
                )

            modality = normalize(
                row["Modality"]
            )

            if modality:

                item["Modalities"].add(
                    modality
                )

                if modality == "DX":
                    item["DXCount"] += 1

                elif modality == "SR":
                    item["SRCount"] += 1

                else:
                    item["OtherModalityCount"] += 1

            body_part = normalize(
                row["BodyPartExamined"]
            )

            if body_part:
                item["BodyParts"].add(
                    body_part
                )

            study_uid = normalize(
                row["StudyInstanceUID"]
            )

            if study_uid:
                item["StudyUIDs"].add(
                    study_uid
                )

            series_uid = normalize(
                row["SeriesInstanceUID"]
            )

            if series_uid:
                item["SeriesUIDs"].add(
                    series_uid
                )

    return unmatched_dicom


# =========================================================
# 載入完整重複匯出
# =========================================================

def load_duplicate_exports(cases):

    if not DUPLICATE_EXPORT_CSV.exists():
        return

    with open(
        DUPLICATE_EXPORT_CSV,
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

            item = cases.get(key)

            if item is None:
                continue

            item["DuplicateExportGroup"] = normalize(
                row["DuplicateExportGroup"]
            )

            item["DuplicateExportStatus"] = (
                "EXACT_DUPLICATE_EXPORT"
            )


# =========================================================
# 分配全域病人匿名 ID
# =========================================================

def assign_global_patient_ids(cases):

    patient_to_anon = {}

    next_id = 1

    # -----------------------------------------------------
    # 第一階段：
    # 有 DICOM PatientID 的，依 PatientID 合併
    # -----------------------------------------------------

    for item in sorted(
        cases.values(),
        key=lambda x: (
            x["Batch"],
            x["ExportID"],
            x["FolderID"]
        )
    ):

        patient_ids = sorted(
            item["PatientIDs"]
        )

        if not patient_ids:
            continue

        # 正常來說一個 case 應該只對一個 PatientID
        primary_patient_id = patient_ids[0]

        if primary_patient_id not in patient_to_anon:

            patient_to_anon[
                primary_patient_id
            ] = f"P{next_id:04d}"

            next_id += 1

        item["GlobalAnonID"] = patient_to_anon[
            primary_patient_id
        ]

    # -----------------------------------------------------
    # 第二階段：
    # JPG-only，沒有 PatientID
    #
    # 暫時每個 case instance 給一個匿名 ID。
    # 後面再用 hash / perceptual hash 做進一步合併。
    # -----------------------------------------------------

    for item in sorted(
        cases.values(),
        key=lambda x: (
            x["Batch"],
            x["ExportID"],
            x["FolderID"]
        )
    ):

        if "GlobalAnonID" in item:
            continue

        item["GlobalAnonID"] = (
            f"P{next_id:04d}"
        )

        next_id += 1

    return patient_to_anon


# =========================================================
# 判斷病例狀態
# =========================================================

def determine_status(item):

    if item["DuplicateExportStatus"]:
        return "DUPLICATE_EXPORT_REVIEW"

    if item["PatientIDs"]:

        if item["DXCount"] > 0:
            return "DICOM_MATCHED"

        return "DICOM_NO_DX_REVIEW"

    return "JPG_ONLY"


# =========================================================
# 建輸出資料
# =========================================================

def build_output(cases):

    private_rows = []
    public_rows = []

    for item in sorted(
        cases.values(),
        key=lambda x: (
            x["GlobalAnonID"],
            x["Batch"],
            x["ExportID"],
            x["FolderID"]
        )
    ):

        patient_ids = " | ".join(
            sorted(item["PatientIDs"])
        )

        body_parts = " | ".join(
            sorted(item["BodyParts"])
        )

        modalities = " | ".join(
            sorted(item["Modalities"])
        )

        status = determine_status(
            item
        )

        private_rows.append({
            "GlobalAnonID":
                item["GlobalAnonID"],

            "Batch":
                item["Batch"],

            "ExportID":
                item["ExportID"],

            "FolderID":
                item["FolderID"],

            "DICOMPatientID":
                patient_ids,

            "JPGCount":
                item["JPGCount"],

            "DXCount":
                item["DXCount"],

            "SRCount":
                item["SRCount"],

            "OtherModalityCount":
                item["OtherModalityCount"],

            "StudyCount":
                len(item["StudyUIDs"]),

            "SeriesCount":
                len(item["SeriesUIDs"]),

            "BodyParts":
                body_parts,

            "Modalities":
                modalities,

            "CaseFingerprint":
                item["CaseFingerprint"],

            "DuplicateExportGroup":
                item["DuplicateExportGroup"],

            "CaseStatus":
                status,

            "Include":
                "",

            "ExcludeReason":
                "",
        })

        public_rows.append({
            "GlobalAnonID":
                item["GlobalAnonID"],

            "JPGCount":
                item["JPGCount"],

            "DXCount":
                item["DXCount"],

            "SRCount":
                item["SRCount"],

            "BodyParts":
                body_parts,

            "Modalities":
                modalities,

            "CaseStatus":
                status,

            "Include":
                "",

            "ExcludeReason":
                "",
        })

    return private_rows, public_rows


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

    print("=" * 90)
    print("建立全域病例 Master")
    print("只讀取既有 CSV，不修改原始影像")
    print("=" * 90)
    print()

    cases = load_jpg_cases()

    print(
        f"JPG case instance：{len(cases)}"
    )

    unmatched_dicom = merge_dicom(
        cases
    )

    load_duplicate_exports(
        cases
    )

    patient_to_anon = assign_global_patient_ids(
        cases
    )

    private_rows, public_rows = build_output(
        cases
    )

    save_csv(
        PRIVATE_OUTPUT,
        private_rows,
        [
            "GlobalAnonID",
            "Batch",
            "ExportID",
            "FolderID",
            "DICOMPatientID",
            "JPGCount",
            "DXCount",
            "SRCount",
            "OtherModalityCount",
            "StudyCount",
            "SeriesCount",
            "BodyParts",
            "Modalities",
            "CaseFingerprint",
            "DuplicateExportGroup",
            "CaseStatus",
            "Include",
            "ExcludeReason",
        ]
    )

    save_csv(
        PUBLIC_OUTPUT,
        public_rows,
        [
            "GlobalAnonID",
            "JPGCount",
            "DXCount",
            "SRCount",
            "BodyParts",
            "Modalities",
            "CaseStatus",
            "Include",
            "ExcludeReason",
        ]
    )

    matched_patient_ids = len(
        patient_to_anon
    )

    jpg_only = sum(
        1
        for row in private_rows
        if row["CaseStatus"] == "JPG_ONLY"
    )

    duplicate_exports = sum(
        1
        for row in private_rows
        if row["CaseStatus"]
        == "DUPLICATE_EXPORT_REVIEW"
    )

    dcm_no_dx = sum(
        1
        for row in private_rows
        if row["CaseStatus"]
        == "DICOM_NO_DX_REVIEW"
    )

    unique_global_ids = len({
        row["GlobalAnonID"]
        for row in private_rows
    })

    print()
    print("=" * 90)
    print("完成")
    print("=" * 90)

    print(
        f"原始 case instance：{len(private_rows)}"
    )

    print(
        f"DICOM 唯一 PatientID："
        f"{matched_patient_ids}"
    )

    print(
        f"目前全域匿名 ID 數："
        f"{unique_global_ids}"
    )

    print(
        f"JPG-only case：{jpg_only}"
    )

    print(
        f"完整重複匯出 instance："
        f"{duplicate_exports}"
    )

    print(
        f"有 DICOM 但無 DX："
        f"{dcm_no_dx}"
    )

    print(
        f"無法對到 JPG case 的 DICOM："
        f"{len(unmatched_dicom)}"
    )

    print()
    print("私密總表：")
    print(PRIVATE_OUTPUT)

    print()
    print("一般工作總表：")
    print(PUBLIC_OUTPUT)

    print()
    print(
        "原始影像沒有被修改。"
    )


if __name__ == "__main__":
    main()