import os
import argparse
from apiclient.discovery import build


DEVELOPER_KEY = os.environ['YOUTUBE_API_KEY']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'


def get_authenticated_service():
    return build(API_SERVICE_NAME, API_VERSION, developerKey=DEVELOPER_KEY)


def channels_list_by_username(client, **kwargs):
    """Returns a list of channels for given username
    """
    return client.channels().list(**kwargs).execute()


def playlist_items_list_by_playlist_id(client, **kwargs):
    """Returns a list of playlist items for given playlist id
    """
    return client.playlistItems().list(**kwargs).execute()


def videos_list_by_id(client, **kwargs):
    """Returns a list of video objects for given video id
    """
    return client.videos().list(**kwargs).execute()


def extract_video_ids(client, playlist_id):
    """Given a playlist id, extracts video ID's and puts them in a list
    """
    response = playlist_items_list_by_playlist_id(
            client, part='contentDetails',
            maxResults=50, playlistId=playlist_id)

    video_ids = []
    while True:
        for item in response['items']:
            video_ids.append(item['contentDetails']['videoId'])

        if 'nextPageToken' not in response:
            break
        else:
            token = response['nextPageToken']
            response = (
                    playlist_items_list_by_playlist_id(
                        client, part='contentDetails',
                        maxResults=50, pageToken=token,
                        playlistId=playlist_id))

    return video_ids


def get_video_stats(client, video_ids):
    """Get video stats for each video_id, extract what is needed
    and put in a list of dicts
    """
    videos = []
    for video_id in video_ids:
        response = videos_list_by_id(client,
                                     part='snippet, statistics', id=video_id)

        title = response['items'][0]['snippet']['title']
        like_count = int(response['items'][0]['statistics']['likeCount'])
        dislike_count = int(response['items'][0]['statistics']['dislikeCount'])
        dtl_ratio = dislike_to_like_ratio(like_count, dislike_count)

        video_dict = {
                'title': title,
                'id': video_id,
                'dtl_ratio': dtl_ratio}
        videos.append(video_dict)

    return videos


def dislike_to_like_ratio(like_count, dislike_count):
    """Calculates controversiality rating based on like/dislike counts
    """
    total = like_count + dislike_count
    if total == 0:
        return 50.0
    else:
        return (dislike_count / total) * 100 if dislike_count != 0 else 0


def sort_by_dtl_ratio(videos):
    """Sorts a list of video objects by like/dislike ration in ascending order
    """
    return sorted(videos, key=lambda x: x['dtl_ratio'], reverse=True)


def print_controversial(videos, count):
    """Prints specified amount of most controversial videos
    """
    if (len(videos) < count):
        print("Channel doesn't have that many videos")
    else:
        for i in range(1, count+1):
            video = videos[i]
            print(f"{i}. {video['title']}\n"
                  f"Link: https://www.youtube.com/watch?v={video['id']}\n"
                  f"Ratio: {round(video['dtl_ratio'], 2)}")


def parse_args():
    """Get channel's name and optional count from the commandline
    """
    parser = argparse.ArgumentParser(
            description="Print youtube channel's controversial videos")
    parser.add_argument('channel', metavar='channel',
                        type=str, help="channel's name")
    parser.add_argument('--count', metavar='count',
                        type=int, help='amount of videos to print', default=5)
    args = parser.parse_args()
    return vars(args)


if __name__ == '__main__':
    args = parse_args()
    username = args['channel']
    count = args['count']

    client = get_authenticated_service()
    channels = channels_list_by_username(
            client, part='contentDetails', forUsername=username)

    uploads_playlist_id = (
            channels['items'][0]['contentDetails']
            ['relatedPlaylists']['uploads'])

    video_ids = extract_video_ids(client, uploads_playlist_id)
    videos = get_video_stats(client, video_ids)
    print_controversial(sort_by_dtl_ratio(videos), count)
