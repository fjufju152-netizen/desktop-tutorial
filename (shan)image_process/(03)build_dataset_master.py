from pathlib import Path
import csv


# =========================================================
# 原始 JPG 病例資料夾
# =========================================================

JPG_ROOT = Path(
    r"C:\Users\Administrator\Desktop\fjuh-機密資料勿外流 Don't disclose confidential Information"
    r"\Temp_DX_260708-260611_200筆"
    r"\20260716_161501_2742"
    r"\IHE_PDI"
    r"\JPG"
)


# =========================================================
# 第二階段產出的 DICOM metadata
# =========================================================

WORK_DIR = Path(
    r"C:\Users\Administrator\Desktop\fjuh-機密資料勿外流 Don't disclose confidential Information"
    r"\shan_process_work"
)

DICOM_METADATA_CSV = WORK_DIR / "dicom_metadata.csv"

OUTPUT_CSV = WORK_DIR / "dataset_master.csv"
PRIVATE_OUTPUT_CSV = WORK_DIR / "dataset_master_private.csv"


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tif",
    ".tiff",
}


def count_jpg_images(folder):
    """
    計算病例資料夾內影像數量。
    """
    count = 0

    for file in folder.rglob("*"):

        if not file.is_file():
            continue

        if file.suffix.lower() in IMAGE_EXTENSIONS:
            count += 1

    return count


def get_jpg_cases():
    """
    取得 JPG_ROOT 下一層所有病例資料夾。
    """

    cases = {}

    if not JPG_ROOT.exists():
        print("[ERROR] 找不到 JPG_ROOT：")
        print(JPG_ROOT)
        return cases

    for folder in JPG_ROOT.iterdir():

        if folder.is_dir():
            cases[folder.name] = folder

    return cases


def load_dicom_metadata():
    """
    讀取 dicom_metadata.csv，
    按 TopFolder 彙整。
    """

    dicom_map = {}

    if not DICOM_METADATA_CSV.exists():
        print("[ERROR] 找不到：")
        print(DICOM_METADATA_CSV)
        return dicom_map

    with open(
        DICOM_METADATA_CSV,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            top_folder = row.get(
                "TopFolder",
                ""
            ).strip()

            if not top_folder:
                continue

            if top_folder not in dicom_map:

                dicom_map[top_folder] = {
                    "PatientIDs": set(),
                    "DXCount": 0,
                    "SRCount": 0,
                    "OtherModalityCount": 0,
                    "Modalities": set(),
                    "BodyParts": set(),
                    "ViewPositions": set(),
                    "StudyUIDs": set(),
                    "SeriesUIDs": set(),
                    "DICOMInstanceCount": 0,
                }

            item = dicom_map[top_folder]

            item["DICOMInstanceCount"] += 1

            patient_id = row.get(
                "PatientID",
                ""
            ).strip()

            if patient_id:
                item["PatientIDs"].add(
                    patient_id
                )

            modality = row.get(
                "Modality",
                ""
            ).strip()

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

            body_part = row.get(
                "BodyPartExamined",
                ""
            ).strip()

            if body_part:
                item["BodyParts"].add(
                    body_part
                )

            view_position = row.get(
                "ViewPosition",
                ""
            ).strip()

            if view_position:
                item["ViewPositions"].add(
                    view_position
                )

            study_uid = row.get(
                "StudyInstanceUID",
                ""
            ).strip()

            if study_uid:
                item["StudyUIDs"].add(
                    study_uid
                )

            series_uid = row.get(
                "SeriesInstanceUID",
                ""
            ).strip()

            if series_uid:
                item["SeriesUIDs"].add(
                    series_uid
                )

    return dicom_map


def main():

    print("=" * 80)
    print("建立 Dataset Master")
    print("本程式只讀取原始資料，不會修改任何原始影像")
    print("=" * 80)
    print()

    jpg_cases = get_jpg_cases()

    print(f"JPG 病例資料夾數：{len(jpg_cases)}")

    dicom_map = load_dicom_metadata()

    print(
        f"DICOM TopFolder 數：{len(dicom_map)}"
    )

    print()

    all_folder_ids = sorted(
        jpg_cases.keys()
    )

    private_records = []
    public_records = []

    matched_dcm_count = 0
    no_dcm_count = 0

    for index, folder_id in enumerate(
        all_folder_ids,
        start=1
    ):

        anon_id = f"P{index:04d}"

        jpg_folder = jpg_cases[folder_id]

        jpg_count = count_jpg_images(
            jpg_folder
        )

        dicom_info = dicom_map.get(
            folder_id
        )

        if dicom_info:

            has_dicom = True
            matched_dcm_count += 1

            patient_ids = " | ".join(
                sorted(
                    dicom_info[
                        "PatientIDs"
                    ]
                )
            )

            dx_count = dicom_info[
                "DXCount"
            ]

            sr_count = dicom_info[
                "SRCount"
            ]

            other_count = dicom_info[
                "OtherModalityCount"
            ]

            dicom_count = dicom_info[
                "DICOMInstanceCount"
            ]

            modalities = " | ".join(
                sorted(
                    dicom_info[
                        "Modalities"
                    ]
                )
            )

            body_parts = " | ".join(
                sorted(
                    dicom_info[
                        "BodyParts"
                    ]
                )
            )

            view_positions = " | ".join(
                sorted(
                    dicom_info[
                        "ViewPositions"
                    ]
                )
            )

            study_count = len(
                dicom_info[
                    "StudyUIDs"
                ]
            )

            series_count = len(
                dicom_info[
                    "SeriesUIDs"
                ]
            )

        else:

            has_dicom = False
            no_dcm_count += 1

            patient_ids = ""
            dx_count = 0
            sr_count = 0
            other_count = 0
            dicom_count = 0
            modalities = ""
            body_parts = ""
            view_positions = ""
            study_count = 0
            series_count = 0

        # =================================================
        # 私密總表
        # =================================================

        private_records.append({

            "PatientAnonID":
                anon_id,

            "FolderID":
                folder_id,

            "DICOMPatientID":
                patient_ids,

            "JPG_Count":
                jpg_count,

            "DICOM_Instance_Count":
                dicom_count,

            "DX_Count":
                dx_count,

            "SR_Count":
                sr_count,

            "Other_Modality_Count":
                other_count,

            "Study_Count":
                study_count,

            "Series_Count":
                series_count,

            "Has_DICOM":
                has_dicom,

            "Modalities":
                modalities,

            "BodyPart":
                body_parts,

            "ViewPositions":
                view_positions,

            # 之後再補
            "Label":
                "",

            "T_Score":
                "",

            "BMD":
                "",

            "Split":
                "",

            "Include":
                "",

            "ExcludeReason":
                "",
        })

        # =================================================
        # 一般模型工作版
        # 不包含 FolderID / PatientID
        # =================================================

        public_records.append({

            "PatientAnonID":
                anon_id,

            "JPG_Count":
                jpg_count,

            "DX_Count":
                dx_count,

            "SR_Count":
                sr_count,

            "Has_DICOM":
                has_dicom,

            "Modalities":
                modalities,

            "BodyPart":
                body_parts,

            "ViewPositions":
                view_positions,

            "Label":
                "",

            "T_Score":
                "",

            "BMD":
                "",

            "Split":
                "",

            "Include":
                "",

            "ExcludeReason":
                "",
        })

        status = (
            "DCM OK"
            if has_dicom
            else "JPG ONLY"
        )

        print(
            f"{anon_id} | "
            f"JPG={jpg_count:<2} | "
            f"DX={dx_count:<2} | "
            f"SR={sr_count:<2} | "
            f"{status}"
        )

    # =====================================================
    # 私密版
    # =====================================================

    private_fields = [
        "PatientAnonID",
        "FolderID",
        "DICOMPatientID",
        "JPG_Count",
        "DICOM_Instance_Count",
        "DX_Count",
        "SR_Count",
        "Other_Modality_Count",
        "Study_Count",
        "Series_Count",
        "Has_DICOM",
        "Modalities",
        "BodyPart",
        "ViewPositions",
        "Label",
        "T_Score",
        "BMD",
        "Split",
        "Include",
        "ExcludeReason",
    ]

    with open(
        PRIVATE_OUTPUT_CSV,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=private_fields
        )

        writer.writeheader()
        writer.writerows(
            private_records
        )

    # =====================================================
    # 一般工作版
    # =====================================================

    public_fields = [
        "PatientAnonID",
        "JPG_Count",
        "DX_Count",
        "SR_Count",
        "Has_DICOM",
        "Modalities",
        "BodyPart",
        "ViewPositions",
        "Label",
        "T_Score",
        "BMD",
        "Split",
        "Include",
        "ExcludeReason",
    ]

    with open(
        OUTPUT_CSV,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=public_fields
        )

        writer.writeheader()
        writer.writerows(
            public_records
        )

    print()
    print("=" * 80)
    print("完成")
    print("=" * 80)

    print(
        f"病例總數："
        f"{len(all_folder_ids)}"
    )

    print(
        f"有 DICOM："
        f"{matched_dcm_count}"
    )

    print(
        f"只有 JPG："
        f"{no_dcm_count}"
    )

    print()

    print("一般工作總表：")
    print(OUTPUT_CSV)

    print()

    print("私密總表：")
    print(PRIVATE_OUTPUT_CSV)

    print()

    print(
        "原始資料沒有被修改。"
    )


if __name__ == "__main__":
    main()