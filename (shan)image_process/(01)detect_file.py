from pathlib import Path
import csv


# =========================================================
# 原始資料位置
# 只讀取，不修改、不刪除、不搬移任何原始資料
# =========================================================

ROOT_DIR = Path(
    r"C:\Users\Administrator\Desktop\fjuh-機密資料勿外流 Don't disclose confidential Information"
    r"\Temp_DX_260708-260611_200筆"
    r"\20260716_161501_2742"
)

JPG_ROOT = ROOT_DIR / "IHE_PDI" / "JPG"
DCM_ROOT = ROOT_DIR / "IMAGE" / "DCM"


# =========================================================
# 輸出位置
# =========================================================

OUTPUT_DIR = Path(
    r"C:\Users\Administrator\Desktop\fjuh-機密資料勿外流 Don't disclose confidential Information"
    r"\shan_process_work"
)

INDEX_FILE = OUTPUT_DIR / "patient_index.csv"
PRIVATE_MAPPING_FILE = OUTPUT_DIR / "private_patient_mapping.csv"


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tif",
    ".tiff",
}


def get_patient_folders(root):
    """
    取得指定資料夾下一層的所有病例資料夾。
    不修改任何檔案。
    """

    if not root.exists():
        print(f"[ERROR] 找不到資料夾：")
        print(root)
        print()
        return {}

    folders = {}

    for folder in root.iterdir():
        if folder.is_dir():
            folders[folder.name] = folder

    return folders


def count_files(folder, image_only=False):
    """
    遞迴計算病例資料夾內檔案數量。
    """

    if folder is None:
        return 0

    count = 0

    for file in folder.rglob("*"):

        if not file.is_file():
            continue

        if image_only:
            if file.suffix.lower() in IMAGE_EXTENSIONS:
                count += 1
        else:
            count += 1

    return count


def main():

    print("=" * 70)
    print("病例資料盤點程式")
    print("本程式只讀取資料，不會修改原始資料")
    print("=" * 70)
    print()

    # -----------------------------------------------------
    # 顯示目前設定的位置
    # -----------------------------------------------------

    print("原始資料根目錄：")
    print(ROOT_DIR)
    print()

    print("JPG 位置：")
    print(JPG_ROOT)
    print()

    print("DCM 位置：")
    print(DCM_ROOT)
    print()

    print("JPG 路徑存在：", JPG_ROOT.exists())
    print("DCM 路徑存在：", DCM_ROOT.exists())

    print()
    print("-" * 70)

    # -----------------------------------------------------
    # 如果兩個資料夾都不存在，直接停止
    # -----------------------------------------------------

    if not JPG_ROOT.exists() and not DCM_ROOT.exists():

        print("[ERROR] JPG 和 DCM 資料夾都找不到。")
        print("請確認 ROOT_DIR 是否正確。")

        return

    # -----------------------------------------------------
    # 建立輸出資料夾
    # 只建立新的工作資料夾，不碰原始資料
    # -----------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print()
    print("輸出資料夾：")
    print(OUTPUT_DIR)
    print()

    # -----------------------------------------------------
    # 取得病例資料夾
    # -----------------------------------------------------

    jpg_patients = get_patient_folders(JPG_ROOT)
    dcm_patients = get_patient_folders(DCM_ROOT)

    print("=" * 70)
    print("掃描結果")
    print("=" * 70)

    print(f"JPG 病例資料夾數：{len(jpg_patients)}")
    print(f"DCM 病例資料夾數：{len(dcm_patients)}")

    # JPG 與 DCM 病例聯集
    all_patient_ids = sorted(
        set(jpg_patients.keys())
        | set(dcm_patients.keys())
    )

    print(f"病例總數：{len(all_patient_ids)}")
    print()

    if len(all_patient_ids) == 0:

        print("[WARNING] 沒有找到病例資料夾。")
        return

    # -----------------------------------------------------
    # 建立資料
    # -----------------------------------------------------

    index_records = []
    private_mapping_records = []

    for index, original_id in enumerate(
        all_patient_ids,
        start=1
    ):

        anon_id = f"P{index:04d}"

        jpg_folder = jpg_patients.get(original_id)
        dcm_folder = dcm_patients.get(original_id)

        jpg_count = count_files(
            jpg_folder,
            image_only=True
        )

        dcm_count = count_files(
            dcm_folder,
            image_only=False
        )

        has_jpg = jpg_folder is not None
        has_dcm = dcm_folder is not None

        matched = has_jpg and has_dcm

        # -------------------------------------------------
        # 一般工作資料
        # 不包含原始病例編號
        # -------------------------------------------------

        index_records.append({
            "PatientAnonID": anon_id,
            "JPG_Count": jpg_count,
            "DCM_Count": dcm_count,
            "Has_JPG": has_jpg,
            "Has_DCM": has_dcm,
            "JPG_DCM_Matched": matched,
        })

        # -------------------------------------------------
        # 私密對照資料
        # 包含原始病例資料夾名稱
        # -------------------------------------------------

        private_mapping_records.append({
            "PatientAnonID": anon_id,
            "OriginalFolderID": original_id,

            "JPG_Folder":
                str(jpg_folder)
                if jpg_folder
                else "",

            "DCM_Folder":
                str(dcm_folder)
                if dcm_folder
                else "",
        })

        status = "OK" if matched else "CHECK"

        print(
            f"{anon_id} | "
            f"JPG={jpg_count:<4} | "
            f"DCM={dcm_count:<4} | "
            f"{status}"
        )

    # -----------------------------------------------------
    # 輸出 patient_index.csv
    # -----------------------------------------------------

    with open(
        INDEX_FILE,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "PatientAnonID",
                "JPG_Count",
                "DCM_Count",
                "Has_JPG",
                "Has_DCM",
                "JPG_DCM_Matched",
            ]
        )

        writer.writeheader()
        writer.writerows(index_records)

    # -----------------------------------------------------
    # 輸出 private_patient_mapping.csv
    # -----------------------------------------------------

    with open(
        PRIVATE_MAPPING_FILE,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "PatientAnonID",
                "OriginalFolderID",
                "JPG_Folder",
                "DCM_Folder",
            ]
        )

        writer.writeheader()
        writer.writerows(private_mapping_records)

    # -----------------------------------------------------
    # 完成
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("完成")
    print("=" * 70)

    print()
    print("一般病例 Index：")
    print(INDEX_FILE)

    print()
    print("私密病例對照表：")
    print(PRIVATE_MAPPING_FILE)

    print()
    print(f"病例總數：{len(all_patient_ids)}")

    print()
    print("原始資料沒有被修改。")


if __name__ == "__main__":
    main()