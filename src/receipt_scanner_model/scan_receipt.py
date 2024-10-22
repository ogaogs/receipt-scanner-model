from PIL import Image, ImageEnhance

import cv2
import numpy as np

import pytesseract
import re

from io import BytesIO

from typing import TypedDict

LANG = "eng+jpn"


class ReceiptAnalyzedData(TypedDict):
    amount: int
    text: str


def preprocess_image(image_bytes: bytes) -> Image.Image:
    """画像の前処理を行う

    Args:
        image_bytes (bytes): 画像のバイトデータ

    Returns:
        Image.Image: 画像データ
    """
    # 画像の読み込み
    img = Image.open(BytesIO(image_bytes))

    # グレースケールに変換
    img = img.convert("L")

    # コントラストを強調
    img = ImageEnhance.Contrast(img).enhance(2)

    # ノイズ除去
    cv2_img = np.array(img, dtype=np.uint8)
    cv2_img = cv2.fastNlMeansDenoising(cv2_img, None, 20)

    # NumPy配列 -> PIL画像
    img = Image.fromarray(cv2_img)
    return img


def extract_text_from_image(image: Image.Image) -> str:
    """画像データをtextに変換

    Args:
        image (Image.Image): 画像データ

    Returns:
        str: 画像のテキストデータ
    """
    return pytesseract.image_to_string(image, lang=LANG)


def extract_amount_from_line(text_line: str) -> int | None:
    """1行ごとの文字列から金額を取得

    Args:
        text_line (str): 1行ごとの文字列

    Returns:
        int | None: 抽出した数字
    """
    # 正規表現で数字を取得する。
    numbers = re.findall(r"\d*[,.]{1}\d{3}|\d+", text_line)

    # 金額は右側に書かれることが多いため、複数ある場合は、最後の値を取得するようにする。
    if len(numbers) > 0:
        return int(re.sub(r"[^\d]", "", numbers[-1]))


def clean_text_line(text_line: str) -> str:
    """空白を削除し行を整える

    Args:
        text_line (str): 1行毎の文字列

    Returns:
        str: 空白をなくした文字列
    """
    return text_line.replace(" ", "").lower()


def get_most_likely(
    kws_amount_dict: dict[str, list[int]], count_amount_dict: dict[int, int]
) -> int:
    """合計金額の可能性がある数字を返す

    Args:
        kws_amount_dict (dict[str, list[int]]): keyにキーワード、valueにそのキーワードに付随する数字
        count_amount_dict (dict[int, int]): keyに抽出された数字、valueに抽出された回数

    Returns:
        int: 最も合計らしい数字
    """
    all_totals = []
    for totals_found in kws_amount_dict.values():
        all_totals += totals_found
    n_unique_totals = len(set(all_totals))
    if n_unique_totals == 1:
        return all_totals[0]

    high_potential_totals = []

    for predictive_keyword in ["合計", "paypay", "クレジット"]:
        predictions = kws_amount_dict.get(predictive_keyword)
        if predictions:
            n_unique_predictions = len(set(predictions))
            if n_unique_predictions == 1:
                high_potential_totals.append(predictions[0])
            else:
                high_potential_totals.append(max(predictions))

    if high_potential_totals:
        return max(high_potential_totals)

    return dict_max(count_amount_dict)


def dict_max(count_amount_dict: dict[int, int]) -> int:
    """合計金額となり得るものを数字の個数や、大きさから判断する

    Args:
        count_amount_dict (dict[int, int]): keyに抽出された数字、valueに抽出された回数

    Returns:
        int: 最も合計らしい数字
    """
    max_counts_list = [
        k for k, v in count_amount_dict.items() if v == max(count_amount_dict.values())
    ]
    dict_len = len(max_counts_list)
    match dict_len:
        case 0:
            return 0
        case 1:
            return max_counts_list[0]
        case _:
            return max(max_counts_list)


def extract_total_amount(text: str) -> int:
    """レシートのテキストデータから合計を取得する

    Args:
        text (str): レシートのテキストデータ

    Returns:
        int: 合計金額
    """
    totals = {}
    # 合計金額が書かれていやすいものを keywords に入れる
    keywords = ["合計", "小計", "計", "言十", "paypay", "クレジット", "キャッシュレス"]
    # 商品の点数など、取得したくないものを illegal_keywords に入れる
    illegal_keywords = ["点数", "お釣り"]

    kws_amount_dict = {word: [] for word in keywords}

    # テキストデータを1行ずつに分け、合計となり得るものを kws_dict に入れていく
    for text_line in text.splitlines():
        text_line_clean = clean_text_line(text_line)
        found = [word for word in keywords if word in text_line_clean]
        found_illegal = [word for word in illegal_keywords if word in text_line_clean]
        if len(found) > 0 and len(found_illegal) == 0:
            total = extract_amount_from_line(text_line_clean)
            if total:
                # totalsに取得したtotalがない場合、追加する
                if not totals.get(total):
                    totals[total] = 1
                # すでにある場合はカウントする
                else:
                    totals[total] = totals[total] + 1

                # kws_dict に totalを追加する
                for i in found:
                    kws_amount_dict[i].append(total)

    return get_most_likely(kws_amount_dict, totals)


def scan(image_bytes: bytes) -> ReceiptAnalyzedData:
    """レシートから最もらしい合計金額を出力する

    Args:
        image_bytes (bytes): 画像のバイトデータ

    Returns:
        ReceiptAnalyzedData: 合計金額とレシートのOCR結果
    """

    # 画像の前処理
    preprocessed_image = preprocess_image(image_bytes)

    # textデータに変換
    text = extract_text_from_image(preprocessed_image)

    # レシートから合計を取得
    total = extract_total_amount(text)

    return {"amount": total, "text": text}
