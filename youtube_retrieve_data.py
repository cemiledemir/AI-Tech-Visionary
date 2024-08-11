from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
import openai
from datetime import datetime, timedelta

# Replace 'YOUR_API_KEY' with your actual API key
api_key = 'YOUR_API_KEY'  # do not forget to delete before GitHub
youtube = build('youtube', 'v3', developerKey=api_key)

# Replace 'YOUR_OPENAI_API_KEY' with your actual OpenAI API key
openai.api_key = 'YOUR_OPENAI_API_KEY'


def search_videos(query, order='relevance', days_ago=1, language='en'):
    published_after = (datetime.now() - timedelta(days=days_ago)).isoformat("T") + "Z"
    request = youtube.search().list(
        part='snippet',
        q=query,
        type='video',
        order=order,  # Use 'relevance', 'date', or 'viewCount'
        maxResults=10,
        publishedAfter=published_after,
        safeSearch='moderate',
        relevanceLanguage=language  # Specify language code here
    )
    response = request.execute()
    return response.get('items', [])


def get_video_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'tr'])
        return ' '.join([entry['text'] for entry in transcript])
    except Exception as e:
        print(f"Could not fetch transcript for video {video_id}: {e}")
        return None


def summarize_transcript(transcript):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an helpful expert in summarizing video transcript."},
                {"role": "user", "content": f"Summarize the following text: {transcript}"}
            ],
            max_tokens=150
        )
        summary = response.choices[0].message['content']
        return summary
    except Exception as e:
        print(f"Could not generate summary: {e}")
        return "Summary not available."


def score_summary_transcript_relevance(transcript, topic):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert in evaluating video content relevance."},
                {"role": "user", "content": f"Evaluate the relevance of the following text to the topic '{topic}': {transcript}"}
            ],
            max_tokens=50
        )
        relevance_score = float(response.choices[0].message['content'])
        return relevance_score
    except Exception as e:
        print(f"Could not evaluate relevance: {e}")
        return 0


def fetch_videos_for_topics(topics):
    all_videos = {}
    for topic in topics:
        latest_relevant_videos = search_videos(topic, order='relevance')
        most_viewed_videos = search_videos(topic, order='viewCount', days_ago=365)  # Fetch videos from the past year

        # Score and filter videos based on summary transcript relevance
        scored_videos_latests = []
        for video in latest_relevant_videos:
            video_id = video['id']['videoId']
            transcript = get_video_transcript(video_id)
            summary = summarize_transcript(transcript) if transcript else "Transcript not available."
            if transcript:
                relevance_score = score_summary_transcript_relevance(summary, topic)
                video['relevance_score'] = relevance_score
                scored_videos_latests.append(video)

        scored_videos_most_viewed = []
        for video in most_viewed_videos:
            video_id = video['id']['videoId']
            transcript = get_video_transcript(video_id)
            summary = summarize_transcript(transcript) if transcript else "Transcript not available."
            if transcript:
                relevance_score = score_summary_transcript_relevance(summary, topic)
                video['relevance_score'] = relevance_score
                scored_videos_most_viewed.append(video)

        # Sort videos by relevance score
        scored_videos_latests.sort(key=lambda x: x['relevance_score'], reverse=True)
        scored_videos_most_viewed.sort(key=lambda x: x['relevance_score'], reverse=True)

        all_videos[topic] = {
            'latest_relevant': latest_relevant_videos,
            'most_viewed': most_viewed_videos
        }
    return all_videos


topics = ['AI', 'Gen AI', 'ML', 'Deep Learning', 'AI in Business', 'GitHub Copilot', 'ChatGPT', 'Google Gemini']
all_videos = fetch_videos_for_topics(topics)

# Display results
for topic, video_categories in all_videos.items():
    print(f"\nLatest and Relevant Videos for topic: {topic}")
    for video in video_categories['latest_relevant']:
        title = video['snippet']['title']
        video_id = video['id']['videoId']
        url = f"https://www.youtube.com/watch?v={video_id}"
        transcript = get_video_transcript(video_id)
        summary = summarize_transcript(transcript) if transcript else "Transcript not available."
        print(f"- {title} ({url})\n  Summary: {summary}")

    print(f"\nMost Viewed Videos for topic: {topic}")
    for video in video_categories['most_viewed']:
        title = video['snippet']['title']
        video_id = video['id']['videoId']
        url = f"https://www.youtube.com/watch?v={video_id}"
        transcript = get_video_transcript(video_id)
        summary = summarize_transcript(transcript) if transcript else "Transcript not available."
        print(f"- {title} ({url})\n  Summary: {summary}")
