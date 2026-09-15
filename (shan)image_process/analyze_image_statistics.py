from pathlib import Path
import math
import warnings

import cv2
import numpy as np
import pandas as pd
from PIL import Image

warnings.filterwarnings("ignore")

# ============================================================
# 設定
# ============================================================

IMAGE_DIR = Path(
    r"C:\Users\Administrator\Desktop\fjuh-機密資料勿外流 Don't disclose confidential Information"
    r"\shan_process_work\final_yolo_dataset\images_all"
)

OUTPUT_DIR = IMAGE_DIR.parent / "image_statistics"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DETAIL_CSV = OUTPUT_DIR / "image_details.csv"
SUMMARY_CSV = OUTPUT_DIR / "summary_statistics.csv"
SIZE_CSV = OUTPUT_DIR / "size_distribution.csv"
FORMAT_CSV = OUTPUT_DIR / "format_summary.csv"
ERROR_CSV = OUTPUT_DIR / "read_errors.csv"

SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"
}


# ============================================================
# 工具函式
# ============================================================

def get_anonymous_id(filename: str) -> str:
    """
    例如：
    P0001_01.jpg -> P0001

    如果你的匿名檔名都是 Pxxxx_xx.jpg，
    這樣就可以直接取得 global anonymous ID。
    """
    stem = Path(filename).stem
    parts = stem.split("_")

    if len(parts) >= 2:
        return parts[0]

    return stem


def calculate_entropy(gray: np.ndarray) -> float:
    """
    Shannon entropy。
    先轉成 256 bins，讓不同影像可以用一致方式比較。
    """
    values = gray.astype(np.float64)

    min_value = values.min()
    max_value = values.max()

    if max_value == min_value:
        return 0.0

    normalized = (
        (values - min_value) /
        (max_value - min_value) * 255
    ).astype(np.uint8)

    hist = cv2.calcHist(
        [normalized],
        [0],
        None,
        [256],
        [0, 256]
    ).ravel()

    probabilities = hist / hist.sum()
    probabilities = probabilities[probabilities > 0]

    return float(
        -np.sum(probabilities * np.log2(probabilities))
    )


def calculate_rms_contrast(gray: np.ndarray) -> float:
    """
    RMS contrast。
    本質上為像素值相對平均值的 RMS。
    """
    values = gray.astype(np.float64)
    mean_value = np.mean(values)

    return float(
        np.sqrt(np.mean((values - mean_value) ** 2))
    )


def calculate_laplacian_variance(gray: np.ndarray) -> float:
    """
    Laplacian variance：
    可作為影像邊緣/清晰度的相對指標。

    注意：
    它不是臨床影像品質的正式診斷指標，
    比較適合用於資料集內部的相對比較。
    """
    values = gray.astype(np.float64)

    # 若不是 8-bit，先正規化，避免 bit depth 造成數值不可比
    min_value = values.min()
    max_value = values.max()

    if max_value == min_value:
        return 0.0

    normalized = (
        (values - min_value) /
        (max_value - min_value) * 255
    ).astype(np.uint8)

    laplacian = cv2.Laplacian(
        normalized,
        cv2.CV_64F
    )

    return float(laplacian.var())


def get_bit_depth(pil_image: Image.Image) -> str:
    """
    回傳 PIL mode 對應的影像資訊。
    JPG 通常為 8-bit/channel。
    """
    mode = pil_image.mode

    mapping = {
        "1": "1-bit",
        "L": "8-bit",
        "P": "8-bit",
        "RGB": "8-bit/channel",
        "RGBA": "8-bit/channel",
        "CMYK": "8-bit/channel",
        "I;16": "16-bit",
        "I;16L": "16-bit",
        "I;16B": "16-bit",
        "I": "32-bit integer",
        "F": "32-bit float",
    }

    return mapping.get(mode, f"Unknown ({mode})")


def convert_to_gray(array: np.ndarray) -> np.ndarray:
    """
    統一取得灰階影像。

    不修改原始檔，只在記憶體內轉換。
    """
    if array.ndim == 2:
        return array

    if array.ndim == 3:
        if array.shape[2] == 3:
            return cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)

        if array.shape[2] == 4:
            return cv2.cvtColor(array, cv2.COLOR_RGBA2GRAY)

    raise ValueError(
        f"Unsupported image shape: {array.shape}"
    )


# ============================================================
# 單張影像分析
# ============================================================

def analyze_image(image_path: Path) -> dict:

    with Image.open(image_path) as img:

        # 讀取基本 metadata
        image_format = img.format
        image_mode = img.mode

        width, height = img.size

        bit_depth = get_bit_depth(img)

        # 轉成 numpy
        array = np.array(img)

    gray = convert_to_gray(array)

    # --------------------------------------------------------
    # 基本資訊
    # --------------------------------------------------------

    file_size_bytes = image_path.stat().st_size
    file_size_kb = file_size_bytes / 1024
    file_size_mb = file_size_bytes / (1024 ** 2)

    total_pixels = width * height
    aspect_ratio = width / height if height else np.nan

    if array.ndim == 2:
        channels = 1
    elif array.ndim == 3:
        channels = array.shape[2]
    else:
        channels = np.nan

    # --------------------------------------------------------
    # 灰階統計
    # --------------------------------------------------------

    pixels = gray.astype(np.float64).ravel()

    minimum = np.min(pixels)
    maximum = np.max(pixels)

    intensity_range = maximum - minimum

    mean = np.mean(pixels)
    median = np.median(pixels)

    # population SD
    std = np.std(pixels)

    q1 = np.percentile(pixels, 25)
    q3 = np.percentile(pixels, 75)
    iqr = q3 - q1

    p1 = np.percentile(pixels, 1)
    p5 = np.percentile(pixels, 5)
    p95 = np.percentile(pixels, 95)
    p99 = np.percentile(pixels, 99)

    robust_range_95_5 = p95 - p5
    robust_range_99_1 = p99 - p1

    # --------------------------------------------------------
    # 額外影像特性
    # --------------------------------------------------------

    entropy = calculate_entropy(gray)
    rms_contrast = calculate_rms_contrast(gray)
    laplacian_variance = calculate_laplacian_variance(gray)

    # --------------------------------------------------------
    # 黑/白像素比例
    #
    # 使用該影像自身 intensity range 的 5% 作為 threshold。
    # 可協助發現黑邊、曝光差異等。
    # --------------------------------------------------------

    if intensity_range > 0:

        low_threshold = minimum + 0.05 * intensity_range
        high_threshold = maximum - 0.05 * intensity_range

        dark_ratio = np.mean(
            pixels <= low_threshold
        ) * 100

        bright_ratio = np.mean(
            pixels >= high_threshold
        ) * 100

    else:

        dark_ratio = 100.0
        bright_ratio = 100.0

    return {

        # 識別
        "Anonymous_ID":
            get_anonymous_id(image_path.name),

        "Filename":
            image_path.name,

        "Relative_Path":
            str(image_path.relative_to(IMAGE_DIR)),

        # 檔案
        "Extension":
            image_path.suffix.lower(),

        "Image_Format":
            image_format,

        "Image_Mode":
            image_mode,

        "Channels":
            channels,

        "Bit_Depth":
            bit_depth,

        "File_Size_Bytes":
            file_size_bytes,

        "File_Size_KB":
            round(file_size_kb, 3),

        "File_Size_MB":
            round(file_size_mb, 5),

        # 尺寸
        "Width":
            width,

        "Height":
            height,

        "Aspect_Ratio":
            round(aspect_ratio, 6),

        "Total_Pixels":
            total_pixels,

        # 灰階
        "Intensity_Min":
            float(minimum),

        "Intensity_Max":
            float(maximum),

        "Intensity_Range_MaxMin":
            float(intensity_range),

        "Intensity_Mean":
            float(mean),

        "Intensity_Median":
            float(median),

        "Intensity_SD":
            float(std),

        "Intensity_Q1":
            float(q1),

        "Intensity_Q3":
            float(q3),

        "Intensity_IQR":
            float(iqr),

        "Intensity_P1":
            float(p1),

        "Intensity_P5":
            float(p5),

        "Intensity_P95":
            float(p95),

        "Intensity_P99":
            float(p99),

        # 比 Max-Min 更穩健的色階跨度
        "Robust_Range_P95_P5":
            float(robust_range_95_5),

        "Robust_Range_P99_P1":
            float(robust_range_99_1),

        # 影像特性
        "Entropy":
            float(entropy),

        "RMS_Contrast":
            float(rms_contrast),

        "Laplacian_Variance":
            float(laplacian_variance),

        "Dark_Pixel_Ratio_Percent":
            float(dark_ratio),

        "Bright_Pixel_Ratio_Percent":
            float(bright_ratio),
    }


# ============================================================
# 主程式
# ============================================================

def main():

    print("=" * 90)
    print("X-ray Image Statistics")
    print("只讀取影像，不修改任何原始 JPG")
    print("=" * 90)

    if not IMAGE_DIR.exists():
        raise FileNotFoundError(
            f"找不到影像資料夾：\n{IMAGE_DIR}"
        )

    image_paths = sorted(
        [
            path
            for path in IMAGE_DIR.rglob("*")
            if (
                path.is_file()
                and path.suffix.lower()
                in SUPPORTED_EXTENSIONS
            )
        ]
    )

    print(f"\n找到影像：{len(image_paths)} 張")
    print(f"來源：{IMAGE_DIR}")
    print(f"輸出：{OUTPUT_DIR}\n")

    records = []
    errors = []

    total = len(image_paths)

    for index, image_path in enumerate(
        image_paths,
        start=1
    ):

        try:

            record = analyze_image(image_path)
            records.append(record)

        except Exception as exc:

            errors.append({
                "Filename": image_path.name,
                "Path": str(image_path),
                "Error": str(exc),
            })

        if (
            index == 1
            or index % 50 == 0
            or index == total
        ):
            print(
                f"[{index}/{total}] "
                f"成功：{len(records)} "
                f"| 失敗：{len(errors)}"
            )

    if not records:
        raise RuntimeError(
            "沒有任何影像成功讀取。"
        )

    # ========================================================
    # 逐張影像明細
    # ========================================================

    detail_df = pd.DataFrame(records)

    detail_df.to_csv(
        DETAIL_CSV,
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # 描述統計
    # ========================================================

    numeric_columns = [
        "File_Size_KB",
        "File_Size_MB",

        "Width",
        "Height",
        "Aspect_Ratio",
        "Total_Pixels",

        "Intensity_Min",
        "Intensity_Max",
        "Intensity_Range_MaxMin",

        "Intensity_Mean",
        "Intensity_Median",
        "Intensity_SD",

        "Intensity_Q1",
        "Intensity_Q3",
        "Intensity_IQR",

        "Intensity_P1",
        "Intensity_P5",
        "Intensity_P95",
        "Intensity_P99",

        "Robust_Range_P95_P5",
        "Robust_Range_P99_P1",

        "Entropy",
        "RMS_Contrast",
        "Laplacian_Variance",

        "Dark_Pixel_Ratio_Percent",
        "Bright_Pixel_Ratio_Percent",
    ]

    summary_rows = []

    for column in numeric_columns:

        series = pd.to_numeric(
            detail_df[column],
            errors="coerce"
        ).dropna()

        if len(series) == 0:
            continue

        summary_rows.append({
            "Variable":
                column,

            "N":
                int(series.count()),

            "Mean":
                float(series.mean()),

            # sample SD for dataset-level descriptive statistics
            "SD":
                float(series.std(ddof=1)),

            "Min":
                float(series.min()),

            "Q1":
                float(series.quantile(0.25)),

            "Median":
                float(series.median()),

            "Q3":
                float(series.quantile(0.75)),

            "Max":
                float(series.max()),
        })

    summary_df = pd.DataFrame(summary_rows)

    summary_df.to_csv(
        SUMMARY_CSV,
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # 尺寸分布
    # ========================================================

    size_df = (
        detail_df
        .groupby(
            ["Width", "Height"],
            dropna=False
        )
        .size()
        .reset_index(name="Count")
        .sort_values(
            "Count",
            ascending=False
        )
    )

    size_df["Percent"] = (
        size_df["Count"] /
        len(detail_df) *
        100
    )

    size_df.to_csv(
        SIZE_CSV,
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # 格式摘要
    # ========================================================

    format_df = (
        detail_df
        .groupby(
            [
                "Extension",
                "Image_Format",
                "Image_Mode",
                "Channels",
                "Bit_Depth"
            ],
            dropna=False
        )
        .size()
        .reset_index(name="Count")
        .sort_values(
            "Count",
            ascending=False
        )
    )

    format_df["Percent"] = (
        format_df["Count"] /
        len(detail_df) *
        100
    )

    format_df.to_csv(
        FORMAT_CSV,
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # Error log
    # ========================================================

    if errors:

        pd.DataFrame(errors).to_csv(
            ERROR_CSV,
            index=False,
            encoding="utf-8-sig"
        )

    # ========================================================
    # 完成
    # ========================================================

    print("\n" + "=" * 90)
    print("分析完成")
    print("=" * 90)

    print(f"成功分析影像：{len(detail_df)}")
    print(f"讀取失敗：{len(errors)}")

    print("\n輸出檔案：")
    print(f"1. {DETAIL_CSV}")
    print(f"2. {SUMMARY_CSV}")
    print(f"3. {SIZE_CSV}")
    print(f"4. {FORMAT_CSV}")

    if errors:
        print(f"5. {ERROR_CSV}")

    print("\n重要欄位：")
    print(
        "Intensity_Range_MaxMin "
        "= 最大灰階 - 最小灰階"
    )

    print(
        "Robust_Range_P95_P5 "
        "= P95 - P5，較不受極端黑白像素影響"
    )

    print(
        "Intensity_SD / RMS_Contrast "
        "= 灰階分散與對比程度"
    )

    print(
        "Laplacian_Variance "
        "= 資料集內部清晰度相對指標"
    )


if __name__ == "__main__":
    main()