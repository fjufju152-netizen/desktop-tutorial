from pathlib import Path
import csv
import shutil


# =========================================================
# 原始 JPG 資料
# 只讀，不修改、不搬移、不刪除
# =========================================================

JPG_ROOT = Path(
    r"C:\Users\Administrator\Desktop\fjuh-機密資料勿外流 Don't disclose confidential Information"
    r"\Temp_DX_260708-260611_200筆"
    r"\20260716_161501_2742"
    r"\IHE_PDI"
    r"\JPG"
)


# =========================================================
# 工作資料夾
# =========================================================

WORK_ROOT = Path(
    r"C:\Users\Administrator\Desktop\fjuh-機密資料勿外流 Don't disclose confidential Information"
    r"\shan_process_work"
)

YOLO_ROOT = WORK_ROOT / "yolo_work"

IMAGES_DIR = YOLO_ROOT / "images_all"
LABELS_DIR = YOLO_ROOT / "labels_all"

MAPPING_CSV = WORK_ROOT / "image_mapping_private.csv"


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tif",
    ".tiff",
}


def get_patient_folders():
    """
    取得所有病例資料夾。
    """
    if not JPG_ROOT.exists():
        print("[ERROR] 找不到 JPG_ROOT：")
        print(JPG_ROOT)
        return []

    folders = [
        folder
        for folder in JPG_ROOT.iterdir()
        if folder.is_dir()
    ]

    return sorted(
        folders,
        key=lambda x: x.name
    )


def get_images(folder):
    """
    取得病例資料夾內所有影像。
    """
    images = []

    for file in folder.rglob("*"):

        if not file.is_file():
            continue

        if file.suffix.lower() in IMAGE_EXTENSIONS:
            images.append(file)

    return sorted(images)


def main():

    print("=" * 80)
    print("準備 YOLO 匿名影像資料集")
    print("只會複製影像，不會修改原始資料")
    print("=" * 80)
    print()

    patient_folders = get_patient_folders()

    if not patient_folders:
        return

    print(f"病例資料夾數：{len(patient_folders)}")
    print()

    # 建立新的工作資料夾
    IMAGES_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    LABELS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    mapping_records = []

    total_images = 0

    for patient_index, patient_folder in enumerate(
        patient_folders,
        start=1
    ):

        anon_patient_id = f"P{patient_index:04d}"

        images = get_images(
            patient_folder
        )

        print(
            f"{anon_patient_id} | "
            f"原始病例={patient_folder.name} | "
            f"影像數={len(images)}"
        )

        for image_index, source_image in enumerate(
            images,
            start=1
        ):

            total_images += 1

            extension = source_image.suffix.lower()

            new_filename = (
                f"{anon_patient_id}_"
                f"{image_index:02d}"
                f"{extension}"
            )

            destination = (
                IMAGES_DIR
                / new_filename
            )

            # =================================================
            # 使用 copy2
            # 只複製，不修改原始影像
            # =================================================

            shutil.copy2(
                source_image,
                destination
            )

            mapping_records.append({
                "PatientAnonID":
                    anon_patient_id,

                "AnonImageName":
                    new_filename,

                "OriginalFolderID":
                    patient_folder.name,

                "OriginalFileName":
                    source_image.name,

                "OriginalPath":
                    str(source_image),

                "CopiedPath":
                    str(destination),
            })

    # =========================================================
    # 建立私密影像對照表
    # =========================================================

    with open(
        MAPPING_CSV,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "PatientAnonID",
                "AnonImageName",
                "OriginalFolderID",
                "OriginalFileName",
                "OriginalPath",
                "CopiedPath",
            ]
        )

        writer.writeheader()
        writer.writerows(
            mapping_records
        )

    print()
    print("=" * 80)
    print("完成")
    print("=" * 80)

    print(f"病例數：{len(patient_folders)}")
    print(f"影像總數：{total_images}")

    print()
    print("匿名影像位置：")
    print(IMAGES_DIR)

    print()
    print("標註資料夾：")
    print(LABELS_DIR)

    print()
    print("私密影像對照表：")
    print(MAPPING_CSV)

    print()
    print(
        "原始影像沒有被修改。"
    )


if __name__ == "__main__":
    main()