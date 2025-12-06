from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from ytmusicapi import YTMusic
import yt_dlp
from typing import List, Dict, Optional
import logging
import httpx

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="YouTube Music Streaming API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MusicService:
    """Service class for handling YouTube Music operations"""
    
    def __init__(self):
        self.ytmusic = YTMusic()
    
    def search_songs(self, query: str, limit: int = 20) -> List[Dict]:
        """Search for songs using ytmusicapi"""
        try:
            results = self.ytmusic.search(query, filter="songs", limit=limit)
            
            songs = []
            for item in results:
                thumbnails = item.get("thumbnails", [])
                thumbnail_url = thumbnails[-1].get("url", "") if thumbnails else ""
                
                song = {
                    "videoId": item.get("videoId", ""),
                    "title": item.get("title", "Unknown Title"),
                    "artist": ", ".join([a["name"] for a in item.get("artists", [])]) if item.get("artists") else "Unknown Artist",
                    "duration": item.get("duration", "0:00"),
                    "thumbnail": thumbnail_url,
                    "album": item.get("album", {}).get("name", "Unknown Album") if item.get("album") else "Unknown Album",
                    "year": item.get("year", "")
                }
                songs.append(song)
            
            return songs
        except Exception as e:
            logger.error(f"Error searching songs: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    
    def get_song_details(self, video_id: str) -> Dict:
        """Get detailed song information"""
        try:
            # Get song info from ytmusicapi
            song_info = self.ytmusic.get_song(video_id)
            
            video_details = song_info.get("videoDetails", {})
            thumbnails = video_details.get("thumbnail", {}).get("thumbnails", [])
            
            return {
                "videoId": video_id,
                "title": video_details.get("title", "Unknown Title"),
                "artist": video_details.get("author", "Unknown Artist"),
                "thumbnail": thumbnails[-1].get("url", "") if thumbnails else "",
                "duration": video_details.get("lengthSeconds", "0"),
                "views": video_details.get("viewCount", "0"),
                "description": video_details.get("shortDescription", "")
            }
        except Exception as e:
            logger.error(f"Error getting song details: {str(e)}")
            return {
                "videoId": video_id,
                "title": "Unknown Title",
                "artist": "Unknown Artist",
                "thumbnail": "",
                "duration": "0",
                "views": "0",
                "description": ""
            }
    
    def get_stream_info(self, video_id: str) -> Dict:
        """Get stream URL with quality options"""
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'nocheckcertificate': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                
                # Get available audio formats
                audio_formats = []
                if 'formats' in info:
                    for fmt in info['formats']:
                        if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                            audio_formats.append({
                                'format_id': fmt.get('format_id', ''),
                                'quality': fmt.get('format_note', 'unknown'),
                                'abr': fmt.get('abr', 0),
                                'url': fmt.get('url', '')
                            })
                
                # Sort by quality (bitrate)
                audio_formats.sort(key=lambda x: x['abr'], reverse=True)
                
                return {
                    'videoId': video_id,
                    'formats': audio_formats,
                    'best_url': audio_formats[0]['url'] if audio_formats else ''
                }
                
        except Exception as e:
            logger.error(f"Error getting stream info: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Stream info retrieval failed: {str(e)}")


# Initialize service
music_service = MusicService()


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "YouTube Music Streaming API", "status": "active"}


@app.get("/search")
async def search_songs(q: str, limit: Optional[int] = 20):
    """
    Search for songs
    
    Parameters:
    - q: Search query
    - limit: Maximum number of results (default: 20)
    """
    if not q or len(q.strip()) == 0:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    
    logger.info(f"Searching for: {q}")
    songs = music_service.search_songs(q, limit)
    
    return {
        "query": q,
        "count": len(songs),
        "results": songs
    }


@app.get("/song/{video_id}")
async def get_song_details(video_id: str):
    """
    Get detailed information about a song
    
    Parameters:
    - video_id: YouTube video ID
    """
    logger.info(f"Getting details for: {video_id}")
    details = music_service.get_song_details(video_id)
    return details


@app.get("/stream/info/{video_id}")
async def get_stream_info(video_id: str):
    """
    Get stream information with quality options
    
    Parameters:
    - video_id: YouTube video ID
    """
    logger.info(f"Getting stream info for: {video_id}")
    stream_info = music_service.get_stream_info(video_id)
    return stream_info


@app.get("/stream/{video_id}")
async def stream_audio(video_id: str, quality: Optional[str] = "best"):
    """
    Stream audio directly (proxy through backend to avoid CORS)
    
    Parameters:
    - video_id: YouTube video ID
    - quality: Audio quality (best, high, medium, low)
    """
    if not video_id or len(video_id.strip()) == 0:
        raise HTTPException(status_code=400, detail="video_id is required")
    
    logger.info(f"Streaming audio for: {video_id} (quality: {quality})")
    
    try:
        # Get stream info
        stream_info = music_service.get_stream_info(video_id)
        stream_url = stream_info['best_url']
        
        # Stream the audio through our backend
        async def stream_generator():
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream('GET', stream_url) as response:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        yield chunk
        
        return StreamingResponse(
            stream_generator(),
            media_type="audio/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Type": "audio/mp4",
                "Cache-Control": "public, max-age=3600"
            }
        )
    except Exception as e:
        logger.error(f"Error streaming audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Streaming failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)