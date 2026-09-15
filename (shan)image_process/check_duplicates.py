from pathlib import Path
import csv
from collections import defaultdict


ROOT = Path(
    r"C:\Users\Administrator\Desktop\fjuh-機密資料勿外流 Don't disclose confidential Information"
    r"\shan_process_work"
)

INPUT_CSV = ROOT / "all_patient_summary_private.csv"

DUPLICATE_CSV = ROOT / "duplicate_patients_private.csv"
UNIQUE_SUMMARY_CSV = ROOT / "unique_patient_summary_private.csv"


def main():

    print("=" * 80)
    print("跨批次 PatientID 去重檢查")
    print("=" * 80)

    patients = defaultdict(list)

    with open(
        INPUT_CSV,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            patient_id = row["PatientID"].strip()

            if not patient_id:
                continue

            if patient_id == "[EMPTY_PATIENT_ID]":
                continue

            patients[patient_id].append(row)

    # =====================================================
    # 統計
    # =====================================================

    duplicate_ids = {
        patient_id: rows
        for patient_id, rows in patients.items()
        if len(rows) > 1
    }

    print()
    print(f"所有批次 PatientID 紀錄數：{sum(len(v) for v in patients.values())}")
    print(f"跨批次唯一 PatientID：{len(patients)}")
    print(f"重複 PatientID 數：{len(duplicate_ids)}")

    # =====================================================
    # 輸出重複病例
    # =====================================================

    duplicate_rows = []

    for patient_id, rows in duplicate_ids.items():

        for row in rows:

            duplicate_rows.append({
                "PatientID": patient_id,
                "Batch": row["Batch"],
                "TopFolders": row["TopFolders"],
                "InstanceCount": row["InstanceCount"],
                "DXCount": row["DXCount"],
                "SRCount": row["SRCount"],
                "BodyParts": row["BodyParts"],
                "Modalities": row["Modalities"],
            })

    with open(
        DUPLICATE_CSV,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        fields = [
            "PatientID",
            "Batch",
            "TopFolders",
            "InstanceCount",
            "DXCount",
            "SRCount",
            "BodyParts",
            "Modalities",
        ]

        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()
        writer.writerows(duplicate_rows)

    # =====================================================
    # 建立唯一 PatientID 總表
    # =====================================================

    unique_rows = []

    for index, (patient_id, rows) in enumerate(
        sorted(patients.items()),
        start=1
    ):

        anon_id = f"P{index:04d}"

        batches = sorted(
            {row["Batch"] for row in rows}
        )

        top_folders = set()
        body_parts = set()
        modalities = set()

        total_dx = 0
        total_sr = 0
        total_instances = 0

        for row in rows:

            total_instances += int(
                row["InstanceCount"] or 0
            )

            total_dx += int(
                row["DXCount"] or 0
            )

            total_sr += int(
                row["SRCount"] or 0
            )

            if row["TopFolders"]:
                top_folders.update(
                    x.strip()
                    for x in row["TopFolders"].split("|")
                    if x.strip()
                )

            if row["BodyParts"]:
                body_parts.update(
                    x.strip()
                    for x in row["BodyParts"].split("|")
                    if x.strip()
                )

            if row["Modalities"]:
                modalities.update(
                    x.strip()
                    for x in row["Modalities"].split("|")
                    if x.strip()
                )

        unique_rows.append({
            "PatientAnonID": anon_id,
            "PatientID": patient_id,
            "BatchCount": len(batches),
            "Batches": " | ".join(batches),
            "TopFolders": " | ".join(sorted(top_folders)),
            "DICOMInstanceCount": total_instances,
            "DXCount": total_dx,
            "SRCount": total_sr,
            "BodyParts": " | ".join(sorted(body_parts)),
            "Modalities": " | ".join(sorted(modalities)),
        })

    with open(
        UNIQUE_SUMMARY_CSV,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        fields = [
            "PatientAnonID",
            "PatientID",
            "BatchCount",
            "Batches",
            "TopFolders",
            "DICOMInstanceCount",
            "DXCount",
            "SRCount",
            "BodyParts",
            "Modalities",
        ]

        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()
        writer.writerows(unique_rows)

    print()
    print("重複病例：")
    print(DUPLICATE_CSV)

    print()
    print("唯一 PatientID 總表：")
    print(UNIQUE_SUMMARY_CSV)

    print()
    print("原始資料沒有被修改。")


if __name__ == "__main__":
    main()