# app/services/query_parser.py
from pydantic import BaseModel
from typing import List
from app.core.config import settings
import json
from openai import AsyncOpenAI
from app.utils.logger import get_logger
import asyncio
from app.utils.text_cleaner import TextCleaner
from app.schemas.scrape import ExtractedRouteInfo

logger = get_logger(__name__)

class ParsedQuery(BaseModel):
    origin: str
    destination: str
    intents: List[str] = ["road_condition"]   # road_condition, weather, safety, news
    confidence: float = 0.9
    raw_query: str = ""

class QueryParserService:
    def __init__(self, max_concurrency: int = 8):  # Groq handles higher concurrency well
        self.client = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )
        self.model = settings.GROQ_MODEL
        self.cleaner = TextCleaner()
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.city_normalizer = {
                    "pindi": "Rawalpindi", "rwp": "Rawalpindi", "lhr": "Lahore",
                    "islamabad": "Islamabad", "khi": "Karachi", "gilgit": "Gilgit",
                    "skardu": "Skardu", "hunza": "Hunza", "peshawar": "Peshawar"
                    # Add more as needed
                }

    async def parse(self, user_input: str) -> ParsedQuery:
        # Simple normalization first
        normalized = user_input.lower()
        for short, full in self.city_normalizer.items():
            normalized = normalized.replace(short, full)

        # Use LLM for robust extraction
        prompt = f"""
        Extract origin city, destination city, and user intent from this travel query.
        Normalize city names properly.
        Return ONLY valid JSON with this schema.

        Query: {user_input}

        Example output:
        {{"origin": "Rawalpindi", "destination": "Skardu", "intents": ["road_condition", "weather"], "confidence": 0.95}}
        """

        try:
            print("We are here? 1")

            response= await self.client.beta.chat.completions.parse(
                    model=self.model,  # or use smaller faster model
                messages=[{"role": "user", "content": prompt}],
                response_format=ParsedQuery,
                temperature=0.0
            )
            data = json.loads(response.choices[0].message.content)

            # Initialize using ONLY the dictionary from the LLM
            parsed = ParsedQuery(**data)

            # Reassign the raw_query field afterward
            parsed.raw_query = user_input
            
            # Final normalization
            parsed.origin = self.city_normalizer.get(parsed.origin.lower(), parsed.origin.title())
            parsed.destination = self.city_normalizer.get(parsed.destination.lower(), parsed.destination.title())
            
            logger.info(f"Parsed query: {parsed.origin} → {parsed.destination}")
            return parsed

        except Exception as e:
            logger.error(f"Query parsing failed: {e}")
            # Fallback: return basic object
            return ParsedQuery(origin="Unknown", destination="Unknown", raw_query=user_input)