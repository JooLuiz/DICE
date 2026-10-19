import itertools
import json
import re
from typing import Any, Dict

import numpy as np
import pandas as pd


def build_feed_template(channel_type: str, use_replies_view: bool = False) -> str:
    suffix = "_Replies" if use_replies_view else ""
    return f"DICE/T_Feed_{channel_type}{suffix}.html"


def read_feed(path: str, delimiter: str) -> pd.DataFrame:
    if re.match(r"^https?://\S+", path):
        if "github" in path:
            return pd.read_csv(path, sep=delimiter)
        if "docs.google.com/spreadsheets" in path:
            sheet_id = path.split("/d/")[1].split("/")[0]
            gid = "0"
            if "gid=" in path:
                gid = path.split("gid=")[1].split("&")[0].split("#")[0]
            export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
            return pd.read_csv(export_url, sep=delimiter)
        if "drive.google.com" in path:
            if "/uc?" in path:
                return pd.read_csv(path, sep=delimiter)
            file_id = path.split("/")[-2]
            download_url = f"https://drive.google.com/uc?id={file_id}"
            return pd.read_csv(download_url, sep=delimiter)
        raise ValueError("Unrecognized URL format")
    return pd.read_csv(path, sep=delimiter)


def is_url(value: Any) -> bool:
    return bool(re.match(r"^https?://", str(value)))


def preprocess_feed(dataframe: pd.DataFrame, step_config: Dict[str, Any]) -> pd.DataFrame:
    dataframe["datetime"] = pd.to_datetime(dataframe["datetime"], errors="coerce", format="%d.%m.%y %H:%M")
    missing_datetime_mask = dataframe["datetime"].isna()
    if missing_datetime_mask.any():
        dataframe.loc[missing_datetime_mask, "datetime"] = pd.to_datetime(
            dataframe.loc[missing_datetime_mask, "datetime"],
            errors="coerce",
        )

    dataframe["datetime"] = dataframe["datetime"].fillna(pd.Timestamp.now())
    dataframe["date"] = dataframe["datetime"].dt.strftime("%d %b").str.replace(" ", ". ")
    dataframe["date"] = dataframe["date"].str.lstrip("0")
    dataframe["formatted_datetime"] = dataframe["datetime"].dt.strftime("%I:%M %p · %b %d, %Y")

    dataframe["text"] = dataframe["text"].str.replace(
        r"\B(\#[a-zA-Z0-9_]+\b)",
        r'<span class="text-primary">\g<0></span>',
        regex=True,
    )
    dataframe["text"] = dataframe["text"].str.replace(
        r"\B(\$[a-zA-Z0-9_\.]+\b)",
        r'<span class="text-primary">\g<0></span>',
        regex=True,
    )
    dataframe["text"] = dataframe["text"].str.replace(
        r"\B(\@[a-zA-Z0-9_]+\b)",
        r'<span class="text-primary">\g<0></span>',
        regex=True,
    )
    dataframe["text"] = dataframe["text"].str.replace(
        r"(http|ftp|https):\/\/([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])",
        r'<a class="text-primary">\g<0></a>',
        regex=True,
    )

    dataframe["replies"] = dataframe["replies"].fillna(0).astype(int)
    dataframe["reposts"] = dataframe["reposts"].fillna(0).astype(int)
    dataframe["likes"] = dataframe["likes"].fillna(0).astype(int)
    dataframe["media"] = dataframe["media"].astype(str).str.replace("'|,", "", regex=True)
    dataframe["pic_available"] = np.where(dataframe["media"].str.contains("http", na=False), True, False)
    dataframe["profile_pic_available"] = dataframe["user_image"].apply(is_url)
    dataframe["icon"] = dataframe["username"].str[:2].str.title()

    color_classes = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8"]
    dataframe["color_class"] = np.random.choice(color_classes, size=len(dataframe))

    dataframe["user_description"] = dataframe["user_description"].str.replace("'", "")
    dataframe["user_description"] = dataframe["user_description"].str.replace('"', "")
    dataframe["user_description"] = dataframe["user_description"].fillna(" ")
    dataframe["user_followers"] = dataframe["user_followers"].map("{:,.0f}".format).str.replace(",", ".")

    condition_column = step_config.get("condition_col")
    if condition_column and condition_column in dataframe.columns and condition_column != "condition":
        dataframe.rename(columns={condition_column: "condition"}, inplace=True)

    if "sequence" not in dataframe.columns:
        dataframe["sequence"] = np.nan

    # A blank "sponsored" cell is read by pandas as NaN, and bool(float('nan')) is True in
    # Python -- without this coercion, every organic row would render as sponsored (templates
    # branch on `{{ if i.sponsored }}`). Coerce to a real boolean so blank/garbage cells are
    # always falsy, and default missing columns to "not sponsored" rather than erroring.
    if "sponsored" in dataframe.columns:
        dataframe["sponsored"] = pd.to_numeric(dataframe["sponsored"], errors="coerce").fillna(0).astype(bool)
    else:
        dataframe["sponsored"] = False

    return dataframe


def prepare_feed_for_round(subsession, step_config: Dict[str, Any]) -> None:
    channel_type = step_config.get("channel_type", "Twitter")
    subsession.FEED = build_feed_template(channel_type=channel_type)

    feed_dataframe = read_feed(path=step_config["data_path"], delimiter=step_config["delimiter"])
    processed_feed = preprocess_feed(dataframe=feed_dataframe, step_config=step_config)

    feed_conditions = None
    if "condition" in processed_feed.columns:
        available_conditions = processed_feed["condition"].dropna().unique()
        if len(available_conditions) > 0:
            feed_conditions = itertools.cycle(available_conditions)
            subsession.feed_conditions = ", ".join(map(str, available_conditions))

    for player in subsession.get_players():
        tweets = processed_feed.copy()
        player.feed_condition = None

        if feed_conditions is not None:
            player.feed_condition = str(next(feed_conditions))
            tweets = tweets[tweets["condition"] == player.feed_condition]

        commented_post_exists = False
        if "commented_post" in tweets.columns:
            if player.feed_condition and "condition" in tweets.columns:
                commented_post_exists = (
                    (tweets["commented_post"] == 1) & (tweets["condition"] == player.feed_condition)
                ).sum() == 1
            else:
                commented_post_exists = (tweets["commented_post"] == 1).sum() == 1

            if commented_post_exists:
                player.subsession.FEED = build_feed_template(channel_type=channel_type, use_replies_view=True)
            tweets.loc[tweets["commented_post"] == 1, "sequence"] = 1
        else:
            tweets["commented_post"] = 0

        tweets.loc[(tweets["sequence"] == 1) & (tweets["commented_post"] == 0), "sequence"] = np.where(
            commented_post_exists,
            np.nan,
            1,
        )

        ranks = np.arange(1, len(tweets) + 1)
        available_ranks = ranks[~np.isin(ranks, tweets["sequence"].dropna())]
        np.random.shuffle(available_ranks)
        missing_indices = tweets["sequence"].isnull()
        tweets.loc[missing_indices, "sequence"] = available_ranks[: sum(missing_indices)]

        tweets.sort_values(by="sequence", inplace=True)
        tweets.reset_index(drop=True, inplace=True)

        # default=str covers the raw "datetime" column (pandas Timestamp objects), which isn't
        # JSON-serializable; this mirrors the implicit str() Jinja already applies today when a
        # template renders {{ i.datetime }} directly (see T_Item_Mass_Media.html).
        player.feed_items_json = json.dumps(tweets.to_dict(orient="index"), default=str)
        if "doc_id" in tweets.columns:
            player.sequence = ", ".join(map(str, tweets["doc_id"].tolist()))
        else:
            player.sequence = ""
        player.step_id = step_config["step_id"]
