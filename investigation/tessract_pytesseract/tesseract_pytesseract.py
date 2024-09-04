from PIL import Image, ImageEnhance

import cv2

import glob
import numpy as np

import pytesseract
import re


LANG = "eng+jpn"


def preprocessing(image_path: str) -> Image.Image:
    """
    画像の前処理を行う
    """
    img = Image.open(image_path)
    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(2)

    cv2_img = np.array(img, dtype=np.uint8)
    cv2_img = cv2.fastNlMeansDenoising(cv2_img, None, 20)

    img = Image.fromarray(cv2_img)
    return img


def get_text(image: Image.Image) -> str:
    """
    画像データをtextに変換
    """
    return pytesseract.image_to_string(image, lang=LANG)


def get_bounding_boxes(image_path: str) -> cv2.typing.MatLike:
    """
    バウンディングボックスを描画し、その画像を返す
    """
    img = cv2.imread(image_path)
    d = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang=LANG)
    n_boxes = len(d["level"])
    for i in range(n_boxes):
        (x, y, w, h) = (d["left"][i], d["top"][i], d["width"][i], d["height"][i])
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
    return img


def find_total_from_line(line):
    """
    1行ごとに金額を取得
    """
    # 正規表現で数字を取得する。
    numbers = re.findall(r"\d*[,.]{1}\d{3}|\d+", line)

    # 金額は右側に書かれることが多いため、複数ある場合は、最後の値を取得するようにする。
    if len(numbers) > 0:
        return int(re.sub(r"[^\d]", "", numbers[-1]))


def clean_line(line):
    """
    空白を削除し行を整える
    """
    return line.replace(" ", "").lower()


# NOTE: dictは型定義をTypedDictとかで行う。
def get_most_likely(keywords_dict: dict[str, list[int]], count_dict: dict) -> int:
    """
    合計金額の可能性がある数字を返す
    """
    all_totals = []
    for totals_found in keywords_dict.values():
        all_totals += totals_found
    n_unique_totals = len(set(all_totals))
    if n_unique_totals == 1:
        return all_totals[0]

    for predictive_keyword in ["合計", "paypay", "クレジット"]:
        predictions = keywords_dict.get(predictive_keyword)
        if predictions:
            n_unique_predictions = len(set(predictions))
            if n_unique_predictions == 1:
                return predictions[0]
            else:
                return max(predictions)
    return dict_max(count_dict)


def dict_max(dict: dict) -> int:
    """
    合計金額となり得るものを数字の個数や、大きさから判断する
    """
    max_counts_dict = [kv for kv in dict.items() if kv[1] == max(dict.values())]
    if len(max_counts_dict) == 1:
        return max_counts_dict[0][0]
    else:
        return max([max_counts_dict[i][0] for i in range(len(max_counts_dict))])


def get_total(text: str) -> int:
    """
    レシートのテキストデータから合計を取得する
    """
    totals = {}
    # 合計金額が書かれていやすいものを keywords に入れる
    keywords = ["合計", "小計", "計", "言十", "paypay", "クレジット", "キャッシュレス"]
    # 商品の点数など、取得したくないものを illegal_keywords に入れる
    illegal_keywords = ["点数", "お釣り"]

    kws_dict = {word: [] for word in keywords}

    # テキストデータを1行ずつに分け、合計となり得るものを kws_dict に入れていく
    for line in text.splitlines():
        line_clean = clean_line(line)
        found = [word for word in keywords if word in line_clean]
        found_illegal = [word for word in illegal_keywords if word in line_clean]
        if len(found) > 0 and len(found_illegal) == 0:
            total = find_total_from_line(line_clean)
            if total is not None:
                # totalsに取得したtotalがない場合、追加する
                if not totals.get(total):
                    totals[total] = 1
                # すでにある場合はカウントする
                else:
                    totals[total] = totals[total] + 1

                # kws_dict に totalを追加する
                for i in found:
                    kws_dict[i].append(total)

    return get_most_likely(kws_dict, totals)


def scan(fp: str, out_dir: str) -> None:
    """
    レシートから最もらしい合計金額を出力する
    """
    receipt_source_name = fp.split("/")[-1].replace(".jpeg", "")
    output_file_name = f"{out_dir}/{receipt_source_name}"

    # 画像の前処理
    preprocessed_image = preprocessing(fp)
    preprocessed_fp = f"{output_file_name}_preprocessed.png"
    preprocessed_image.save(preprocessed_fp)

    # textデータに変換
    text = get_text(preprocessed_image)
    with open(f"{output_file_name}.txt", "w") as f:
        f.writelines(text)

    # バウンディングボックスの取得
    bounding_boxed_image = get_bounding_boxes(preprocessed_fp)
    cv2.imwrite(f"{output_file_name}_boxes.png", bounding_boxed_image)

    # get the receipt total value
    total = get_total(text)
    print(total)


# NOTE: ファイル名などをコマンドラインから取れるようにする。
def main() -> None:
    """
    実行するmain関数
    """
    out_dir = "output"
    for fp in glob.glob("raw/*"):
        scan(fp=fp, out_dir=out_dir)


if __name__ == "__main__":
    main()
