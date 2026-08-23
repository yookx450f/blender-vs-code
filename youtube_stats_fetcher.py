"""
YouTube 統計データ取得モジュール

YouTube Data API v3 を使って動画の視聴回数・高評価数・コメント数を取得する。
"""

import os
import re
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# .env ファイルを読み込み（プロジェクトルートから）
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# ロガー設定（Streamlitコンソール出力対応）
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def get_youtube_api_key() -> Optional[str]:
    """環境変数または.envからYouTube APIキーを取得"""
    return os.environ.get("YOUTUBE_API_KEY", None)


def get_video_id_from_url(url: str) -> Optional[str]:
    """
    YouTube URL から動画IDを抽出する。

    対応フォーマット:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://youtube.com/shorts/VIDEO_ID
    - VIDEO_ID (裸のID)
    """
    if not url or not isinstance(url, str):
        return None

    url = url.strip()
    if not url:
        return None

    # 裸の動画ID（11文字の英数字）
    if re.match(r"^[a-zA-Z0-9_-]{11}$", url):
        return url

    # watch?v= パターン
    match = re.search(r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})", url)
    if match:
        return match.group(1)

    # youtu.be/ パターン
    match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", url)
    if match:
        return match.group(1)

    # youtube.com/shorts/ パターン
    match = re.search(r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})", url)
    if match:
        return match.group(1)

    return None


def _build_youtube_service(api_key: str):
    """YouTube Data API v3 サービスオブジェクトを構築"""
    try:
        return build("youtube", "v3", developerKey=api_key)
    except Exception as e:
        raise RuntimeError(f"YouTubeサービス構築に失敗しました: {e}")


def fetch_video_stats(video_ids: List[str], api_key: str) -> Dict[str, Dict[str, int]]:
    """
    YouTube Data API v3 で動画統計をバッチ取得する。

    Args:
        video_ids: 動画IDのリスト（最大50件まで）
        api_key: YouTube Data API v3 のAPIキー

    Returns:
        {video_id: {"viewCount": int, "likeCount": int, "commentCount": int}}
        （エラーになった動画IDは含まれない）
    """
    if not video_ids:
        logger.warning("動画IDリストが空です")
        return {}

    logger.info(f"YouTube API 呼び出し開始: {len(video_ids)}件の動画ID")
    yt_service = _build_youtube_service(api_key)
    results = {}

    # 50件ずつバッチ処理
    batch_size = 50
    for i in range(0, len(video_ids), batch_size):
        batch_ids = video_ids[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(video_ids) + batch_size - 1) // batch_size
        logger.info(f"バッチ {batch_num}/{total_batches}: {len(batch_ids)}件の動画IDをリクエスト")
        
        try:
            request = yt_service.videos().list(
                part="statistics",
                id=",".join(batch_ids)
            )
            response = request.execute()

            items = response.get("items", [])
            logger.info(f"バッチ {batch_num}: APIから {len(items)}件の動画データを取得")

            for item in items:
                vid = item["id"]
                stats = item.get("statistics", {})
                
                # 各フィールドの生値をログ出力（デバッグ用）
                raw_view = stats.get("viewCount", "MISSING")
                raw_like = stats.get("likeCount", "MISSING")
                raw_comment = stats.get("commentCount", "MISSING")
                raw_disabled = stats.get("disabled", "MISSING")
                
                result = {
                    "viewCount": int(stats.get("viewCount", 0)),
                    "likeCount": int(stats.get("likeCount", 0)),
                    "commentCount": int(stats.get("commentCount", 0))
                }
                results[vid] = result
                logger.info(f"  [{vid}] 👁{result['viewCount']:,} 👍{result['likeCount']:,} 💬{result['commentCount']:,}")
                logger.debug(f"    生データ: view={raw_view}, like={raw_like}, comment={raw_comment}, disabled={raw_disabled}")

            # リクエストしたIDの中でAPIから返ってこなかったものをログ
            returned_ids = set(item["id"] for item in items)
            missing_ids = set(batch_ids) - returned_ids
            if missing_ids:
                logger.warning(f"バッチ {batch_num}: {len(missing_ids)}件の動画がAPIレスポンスに含まれていない (非公開/削除済み?): {missing_ids}")

        except HttpError as e:
            error_body = ""
            try:
                error_body = e.content.decode("utf-8") if hasattr(e, 'content') and e.content else ""
            except:
                pass
            logger.error(f"YouTube API エラー (バッチ {batch_num}): {e}")
            if error_body:
                logger.error(f"エラー詳細: {error_body[:500]}")
            raise RuntimeError(f"YouTube API エラー: {e}") from e

    logger.info(f"YouTube API 呼び出し完了: 合計 {len(results)}件の動画データを取得")
    return results


def fetch_stats_for_comparisons(
    comparisons: List[Dict[str, Any]]
) -> Dict[str, Dict]:
    """
    比較ペアリストから動画URLを抽出し、YouTube統計を一括取得する。

    Args:
        comparisons: 比較ペアのリスト（辞書）。
            各要素に short_video_url, long_video_url が含まれていること。

    Returns:
        {
            "stats": {comp_id: {"short": {...}, "long": {...}}},
            "errors": [(comp_id, error_message), ...],
            "log": [ログメッセージリスト]  # UI表示用
        }
    """
    api_key = get_youtube_api_key()
    if not api_key:
        logger.error("YouTube APIキーが設定されていません")
        raise RuntimeError("YouTube APIキーが設定されていません。")

    # UI表示用のログリスト
    ui_log = []
    def log_msg(msg):
        logger.info(msg)
        ui_log.append(msg)

    log_msg(f"🚀 比較ペア処理開始: {len(comparisons)}件のペア")

    # 動画IDを収集（重複除去）
    video_id_map: Dict[str, List[tuple]] = {}  # video_id -> [(comp_id, video_type), ...]
    url_parse_errors = []
    
    for comp in comparisons:
        comp_id = comp["id"]
        short_url = comp.get("short_video_url", "") or ""
        long_url = comp.get("long_video_url", "") or ""

        short_vid = get_video_id_from_url(short_url)
        if short_vid:
            video_id_map.setdefault(short_vid, []).append((comp_id, "short"))
        elif short_url:
            err = f"⚠️ comp_id={comp_id}: ショートURLから動画IDを抽出失敗 ({short_url})"
            url_parse_errors.append(err)

        long_vid = get_video_id_from_url(long_url)
        if long_vid:
            video_id_map.setdefault(long_vid, []).append((comp_id, "long"))
        elif long_url:
            err = f"⚠️ comp_id={comp_id}: 長尺URLから動画IDを抽出失敗 ({long_url})"
            url_parse_errors.append(err)

    for err in url_parse_errors:
        log_msg(err)

    log_msg(f"📋 動画ID収集完了: {len(video_id_map)}件の固有動画ID (重複除去後)")

    if not video_id_map:
        log_msg("⚠️ 取得対象の動画がありません")
        return {"stats": {}, "errors": [], "log": ui_log}

    # YouTube API で一括取得
    all_video_ids = list(video_id_map.keys())
    try:
        api_results = fetch_video_stats(all_video_ids, api_key)
    except RuntimeError as e:
        log_msg(f"❌ API呼び出し失敗: {e}")
        raise e

    # 結果を比較ペアにマッピング
    stats = {}
    errors = []
    for comp in comparisons:
        comp_id = comp["id"]
        comp_stats = {"short": None, "long": None}

        short_url = comp.get("short_video_url", "") or ""
        long_url = comp.get("long_video_url", "") or ""

        short_vid = get_video_id_from_url(short_url)
        if short_vid and short_vid in api_results:
            comp_stats["short"] = api_results[short_vid]
            s = api_results[short_vid]
            log_msg(f"  ✅ comp_id={comp_id} ショート: 👁{s['viewCount']:,} 👍{s['likeCount']:,} 💬{s['commentCount']:,}")
        elif short_vid:
            err_msg = f"❌ comp_id={comp_id}: ショート動画({short_vid})の統計取得失敗"
            errors.append(err_msg)
            log_msg(err_msg)

        long_vid = get_video_id_from_url(long_url)
        if long_vid and long_vid in api_results:
            comp_stats["long"] = api_results[long_vid]
            l = api_results[long_vid]
            log_msg(f"  ✅ comp_id={comp_id} 長尺: 👁{l['viewCount']:,} 👍{l['likeCount']:,} 💬{l['commentCount']:,}")
        elif long_vid:
            err_msg = f"❌ comp_id={comp_id}: 長尺動画({long_vid})の統計取得失敗"
            errors.append(err_msg)
            log_msg(err_msg)

        # 少なくとも片方の動画が取得成功した場合のみ保存
        if comp_stats["short"] or comp_stats["long"]:
            stats[comp_id] = comp_stats

    log_msg(f"📊 統計マッピング完了: {len(stats)}件のペアにデータを割り当て")
    if errors:
        log_msg(f"⚠️ エラー合計: {len(errors)}件")

    return {"stats": stats, "errors": errors, "log": ui_log}
