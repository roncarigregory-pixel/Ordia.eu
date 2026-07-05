"""Ordia AI Marketing Agent — Phase 1 (modular, brand-configurable, admin-only).

Nothing is hardcoded to Ordia: everything derives from a configurable Brand Profile
(company name, logo, colors, website, industry, products, audience, tone, languages,
goals, CTAs, social accounts, publish webhook). Ordia is simply the first brand seeded
as editable data. Designed so publishing (n8n/Make webhook now; native OAuth later),
analytics and AI-learning can be added without changing this architecture.

Text generation: Claude Sonnet 4.6 via emergentintegrations.
Image generation: Gemini Nano Banana (gemini-3.1-flash-image-preview).
Both are provider-swappable via the small helpers below.
"""
import json
import uuid
import base64
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

import httpx
from fastapi import Depends, HTTPException, Request, Response
from pydantic import BaseModel
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger("ordia.marketing")

# Reusable taxonomies (config, not code-locked to Ordia).
CATEGORIES = [
    "product_updates", "customer_success", "industry_insights", "ai_automation",
    "erp_integrations", "order_management_tips", "behind_the_scenes", "founder_journey",
    "product_demos", "feature_highlights", "statistics", "faqs", "testimonials",
    "case_studies", "lead_generation",
]
CHANNELS = ["linkedin", "twitter", "facebook", "instagram", "blog", "newsletter",
            "product_announcement", "video_script", "youtube_description",
            "short_form_idea", "carousel", "poll", "cta_variations"]

CHANNEL_GUIDE = {
    "linkedin": "Professional but human. 1-3 short paragraphs, a strong hook first line, 3-5 relevant hashtags, clear CTA.",
    "twitter": "Punchy, <= 280 characters, 1-2 hashtags, a hook. Optionally a short thread of 3 tweets in body separated by \\n\\n.",
    "facebook": "Conversational, friendly, 1-2 short paragraphs, 1 emoji max, soft CTA.",
    "instagram": "Engaging caption, line breaks, 1-2 emojis, 5-10 hashtags at the end, CTA to link in bio.",
    "blog": "Long-form article (600-900 words) with structured H2/H3 headings, intro, body, conclusion.",
    "newsletter": "Email newsletter: subject line as title, warm greeting, scannable sections, single clear CTA button text.",
    "product_announcement": "Concise announcement: what's new, why it matters, CTA.",
    "video_script": "30-60s script with scene breakdown, spoken lines, and on-screen text cues.",
    "youtube_description": "SEO-friendly description with summary, timestamps placeholder, links and hashtags.",
    "short_form_idea": "A short-form video idea: hook, 3 beats, CTA, suggested on-screen text.",
    "carousel": "Carousel: return 5-7 slides in body, each 'Slide N: <text>', last slide is the CTA.",
    "poll": "A poll: a question and 2-4 options in the body.",
    "cta_variations": "Return 5 distinct call-to-action variations in the body, one per line.",
}

STATUSES = ["idea", "draft", "review", "approved", "scheduled", "published"]


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def setup_marketing(api, ctx):
    db = ctx["db"]
    get_current_user = ctx["get_current_user"]
    require_privileged = ctx["require_privileged"]
    EMERGENT_LLM_KEY = ctx["EMERGENT_LLM_KEY"]

    # ----- Brand profile (configurable; Ordia seeded as editable default) -----
    DEFAULT_BRAND = {
        "company_name": "Ordia",
        "logo_url": "",
        "brand_colors": ["#0f172a", "#6366f1"],
        "website": "https://ordia.eu",
        "industry": "B2B order automation for wholesale distributors",
        "products": "AI that turns WhatsApp, email, PDF and photo orders into clean orders integrated with your ERP.",
        "target_audience": "Wholesale distributors, food & beverage suppliers, sales/ops managers.",
        "tone_of_voice": "Confident, clear, practical, human. No hype.",
        "languages": ["en", "it"],
        "marketing_goals": ["early access signups", "book a demo", "brand awareness"],
        "ctas": ["Request early access", "Book a demo", "Join the waitlist"],
        "social_accounts": {"linkedin": "", "twitter": "", "facebook": "", "instagram": "", "youtube": ""},
        "publish_webhook_url": "",
    }

    class BrandProfile(BaseModel):
        company_name: Optional[str] = None
        logo_url: Optional[str] = None
        brand_colors: Optional[List[str]] = None
        website: Optional[str] = None
        industry: Optional[str] = None
        products: Optional[str] = None
        target_audience: Optional[str] = None
        tone_of_voice: Optional[str] = None
        languages: Optional[List[str]] = None
        marketing_goals: Optional[List[str]] = None
        ctas: Optional[List[str]] = None
        social_accounts: Optional[dict] = None
        publish_webhook_url: Optional[str] = None

    async def get_brand(company_id: str) -> dict:
        doc = await db.mkt_brands.find_one({"company_id": company_id}, {"_id": 0})
        if not doc:
            doc = {"company_id": company_id, **DEFAULT_BRAND,
                   "created_at": _now_iso(), "updated_at": _now_iso()}
            await db.mkt_brands.insert_one(dict(doc))
            doc.pop("_id", None)
        return doc

    def _brand_context(brand: dict) -> str:
        return (
            f"BRAND: {brand.get('company_name')}\n"
            f"Website: {brand.get('website')}\n"
            f"Industry: {brand.get('industry')}\n"
            f"Products/Services: {brand.get('products')}\n"
            f"Target audience: {brand.get('target_audience')}\n"
            f"Tone of voice: {brand.get('tone_of_voice')}\n"
            f"Marketing goals: {', '.join(brand.get('marketing_goals') or [])}\n"
            f"Preferred CTAs: {', '.join(brand.get('ctas') or [])}\n"
        )

    async def _llm_json(system: str, prompt: str) -> dict:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"mkt-{uuid.uuid4()}",
                       system_message=system).with_model("anthropic", "claude-sonnet-4-6")
        resp = await chat.send_message(UserMessage(text=prompt))
        text = resp.strip() if isinstance(resp, str) else str(resp)
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.lstrip().startswith("json"):
                text = text.lstrip()[4:]
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start, end = text.find("{"), text.rfind("}")
            if start == -1:
                start, end = text.find("["), text.rfind("]")
            return json.loads(text[start:end + 1])

    # ---------------------------- Brand endpoints ----------------------------
    @api.get("/marketing/brand")
    async def read_brand(user: dict = Depends(get_current_user)):
        require_privileged(user)
        return await get_brand(user["company_id"])

    @api.put("/marketing/brand")
    async def update_brand(body: BrandProfile, user: dict = Depends(get_current_user)):
        require_privileged(user)
        await get_brand(user["company_id"])
        upd = {k: v for k, v in body.model_dump().items() if v is not None}
        upd["updated_at"] = _now_iso()
        await db.mkt_brands.update_one({"company_id": user["company_id"]}, {"$set": upd})
        return await get_brand(user["company_id"])

    # -------------------------- Content generation ---------------------------
    class GenerateRequest(BaseModel):
        channel: str
        category: str
        content_type: Optional[str] = None
        topic: Optional[str] = None
        language: Optional[str] = "en"

    def _content_system(brand: dict) -> str:
        return (
            "You are an expert B2B marketing content writer and strategist.\n"
            "You write channel-optimized, high-converting content that is never generic.\n"
            "Always return STRICT JSON only, no prose, no code fences.\n\n" + _brand_context(brand)
        )

    async def _generate_content(brand, channel, category, topic, language):
        guide = CHANNEL_GUIDE.get(channel, "Write optimized content for this channel.")
        prompt = (
            f"Create a single piece of marketing content.\n"
            f"Channel: {channel}\nCategory: {category}\n"
            f"Topic (optional): {topic or 'choose the most relevant angle for the category'}\n"
            f"Language: {language}\n\nChannel rules: {guide}\n\n"
            "Optimize for lead generation toward the brand's CTAs when natural.\n"
            "Return JSON with EXACTLY these keys: "
            '{"title": str, "body": str, "hashtags": [str], "cta": str, '
            '"image_prompt": str (a vivid prompt to generate a matching branded visual), '
            '"seo": {"meta_title": str, "meta_description": str, "keywords": [str], "headings": [str]}}'
        )
        data = await _llm_json(_content_system(brand), prompt)
        return data

    @api.post("/marketing/generate")
    async def generate_content(body: GenerateRequest, user: dict = Depends(get_current_user)):
        require_privileged(user)
        if body.channel not in CHANNELS:
            raise HTTPException(status_code=400, detail=f"Canale non valido: {body.channel}")
        brand = await get_brand(user["company_id"])
        data = await _generate_content(brand, body.channel, body.category, body.topic, body.language)
        doc = {
            "id": str(uuid.uuid4()), "company_id": user["company_id"],
            "channel": body.channel, "category": body.category,
            "content_type": body.content_type or body.channel,
            "language": body.language or "en",
            "title": data.get("title", ""), "body": data.get("body", ""),
            "hashtags": data.get("hashtags", []) or [], "cta": data.get("cta", ""),
            "image_prompt": data.get("image_prompt", ""), "image_url": None,
            "seo": data.get("seo", {}) or {},
            "status": "draft", "scheduled_at": None, "published_at": None,
            "created_at": _now_iso(), "updated_at": _now_iso(),
            "created_by": user.get("email"),
        }
        await db.mkt_content.insert_one(dict(doc))
        doc.pop("_id", None)
        return doc

    # ------------------------------ SEO blog ---------------------------------
    class BlogRequest(BaseModel):
        topic: str
        keywords: Optional[List[str]] = None
        language: Optional[str] = "en"

    @api.post("/marketing/blog")
    async def generate_blog(body: BlogRequest, user: dict = Depends(get_current_user)):
        require_privileged(user)
        brand = await get_brand(user["company_id"])
        prompt = (
            f"Write a complete SEO-optimized blog article.\nTopic: {body.topic}\n"
            f"Target keywords: {', '.join(body.keywords or []) or 'infer the best keywords'}\n"
            f"Language: {body.language}\n\n"
            "Use structured H2/H3 headings, an engaging intro, actionable body, and a conclusion "
            "with a CTA toward the brand's goals. 600-900 words.\n"
            "Return JSON: {\"title\": str, \"body\": str (markdown with ## and ### headings), "
            "\"cta\": str, \"seo\": {\"meta_title\": str, \"meta_description\": str, "
            "\"keywords\": [str], \"headings\": [str]}, \"image_prompt\": str}"
        )
        data = await _llm_json(_content_system(brand), prompt)
        doc = {
            "id": str(uuid.uuid4()), "company_id": user["company_id"],
            "channel": "blog", "category": "industry_insights", "content_type": "blog",
            "language": body.language or "en",
            "title": data.get("title", ""), "body": data.get("body", ""),
            "hashtags": [], "cta": data.get("cta", ""),
            "image_prompt": data.get("image_prompt", ""), "image_url": None,
            "seo": data.get("seo", {}) or {},
            "status": "draft", "scheduled_at": None, "published_at": None,
            "created_at": _now_iso(), "updated_at": _now_iso(), "created_by": user.get("email"),
        }
        await db.mkt_content.insert_one(dict(doc))
        doc.pop("_id", None)
        return doc

    # -------------------------- Calendar planning ----------------------------
    class CalendarRequest(BaseModel):
        period: str = "weekly"        # daily | weekly | monthly
        start_date: Optional[str] = None   # ISO date
        count: Optional[int] = None
        channels: Optional[List[str]] = None

    @api.post("/marketing/calendar/generate")
    async def generate_calendar(body: CalendarRequest, user: dict = Depends(get_current_user)):
        require_privileged(user)
        brand = await get_brand(user["company_id"])
        span = {"daily": 1, "weekly": 7, "monthly": 30}.get(body.period, 7)
        count = body.count or {"daily": 2, "weekly": 7, "monthly": 20}.get(body.period, 7)
        count = max(1, min(count, 40))
        channels = [c for c in (body.channels or ["linkedin", "instagram", "twitter", "facebook", "blog", "newsletter"]) if c in CHANNELS]
        try:
            start = datetime.fromisoformat(body.start_date) if body.start_date else datetime.now(timezone.utc)
        except ValueError:
            start = datetime.now(timezone.utc)
        prompt = (
            f"Plan a BALANCED marketing content calendar of {count} items spread over {span} day(s).\n"
            f"Use these channels: {', '.join(channels)}.\n"
            f"Use a healthy mix of these categories (avoid repetition, vary formats): {', '.join(CATEGORIES)}.\n"
            "Distribute categories evenly and never repeat the same category twice in a row.\n"
            "Return JSON: {\"items\": [{\"day_offset\": int (0..%d), \"channel\": str, "
            "\"category\": str, \"content_type\": str, \"title\": str, \"hook\": str}]}" % (span - 1)
        )
        data = await _llm_json(_content_system(brand), prompt)
        items = data.get("items", [])[:count]
        docs = []
        for it in items:
            try:
                off = int(it.get("day_offset", 0))
            except (ValueError, TypeError):
                off = 0
            ch = it.get("channel") if it.get("channel") in CHANNELS else channels[0]
            doc = {
                "id": str(uuid.uuid4()), "company_id": user["company_id"],
                "channel": ch, "category": it.get("category", "product_updates"),
                "content_type": it.get("content_type") or ch, "language": "en",
                "title": it.get("title", ""), "body": it.get("hook", ""),
                "hashtags": [], "cta": "", "image_prompt": "", "image_url": None, "seo": {},
                "status": "idea",
                "scheduled_at": (start + timedelta(days=max(0, min(off, span - 1)))).isoformat(),
                "published_at": None, "created_at": _now_iso(), "updated_at": _now_iso(),
                "created_by": user.get("email"),
            }
            docs.append(doc)
        if docs:
            await db.mkt_content.insert_many([dict(d) for d in docs])
            for d in docs:
                d.pop("_id", None)
        return {"items": docs, "count": len(docs)}

    # ---------------------------- Recommendations ----------------------------
    @api.get("/marketing/recommendations")
    async def recommendations(user: dict = Depends(get_current_user)):
        require_privileged(user)
        brand = await get_brand(user["company_id"])
        recent = await db.mkt_content.find({"company_id": user["company_id"]}, {"_id": 0, "title": 1, "category": 1}).sort("created_at", -1).to_list(20)
        titles = "; ".join(f"{r.get('category')}: {r.get('title')}" for r in recent) or "none yet"
        prompt = (
            f"Recent content titles: {titles}.\n"
            "Suggest 5 fresh, high-impact content ideas that fill gaps and drive lead generation. "
            "Return JSON: {\"ideas\": [{\"title\": str, \"channel\": str, \"category\": str, \"why\": str}]}"
        )
        data = await _llm_json(_content_system(brand), prompt)
        return {"ideas": data.get("ideas", [])}

    # ------------------------------ Content CRUD ------------------------------
    class ContentUpdate(BaseModel):
        title: Optional[str] = None
        body: Optional[str] = None
        hashtags: Optional[List[str]] = None
        cta: Optional[str] = None
        image_prompt: Optional[str] = None
        seo: Optional[dict] = None
        status: Optional[str] = None
        scheduled_at: Optional[str] = None
        category: Optional[str] = None
        channel: Optional[str] = None

    @api.get("/marketing/content")
    async def list_content(user: dict = Depends(get_current_user),
                           status: Optional[str] = None, channel: Optional[str] = None):
        require_privileged(user)
        q = {"company_id": user["company_id"]}
        if status and status != "all":
            q["status"] = status
        if channel and channel != "all":
            q["channel"] = channel
        items = await db.mkt_content.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
        return {"items": items, "total": len(items)}

    @api.get("/marketing/stats")
    async def content_stats(user: dict = Depends(get_current_user)):
        require_privileged(user)
        cid = user["company_id"]
        out = {}
        for s in STATUSES:
            out[s] = await db.mkt_content.count_documents({"company_id": cid, "status": s})
        out["total"] = await db.mkt_content.count_documents({"company_id": cid})
        return out

    async def _get_item(cid, item_id):
        doc = await db.mkt_content.find_one({"id": item_id, "company_id": cid}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Contenuto non trovato")
        return doc

    @api.get("/marketing/content/{item_id}")
    async def get_content(item_id: str, user: dict = Depends(get_current_user)):
        require_privileged(user)
        return await _get_item(user["company_id"], item_id)

    @api.put("/marketing/content/{item_id}")
    async def update_content(item_id: str, body: ContentUpdate, user: dict = Depends(get_current_user)):
        require_privileged(user)
        await _get_item(user["company_id"], item_id)
        if body.status and body.status not in STATUSES:
            raise HTTPException(status_code=400, detail="Stato non valido")
        upd = {k: v for k, v in body.model_dump().items() if v is not None}
        upd["updated_at"] = _now_iso()
        await db.mkt_content.update_one({"id": item_id, "company_id": user["company_id"]}, {"$set": upd})
        return await _get_item(user["company_id"], item_id)

    @api.delete("/marketing/content/{item_id}")
    async def delete_content(item_id: str, user: dict = Depends(get_current_user)):
        require_privileged(user)
        await db.mkt_content.delete_one({"id": item_id, "company_id": user["company_id"]})
        return {"ok": True}

    # ----------------------- Approval / schedule / publish --------------------
    @api.post("/marketing/content/{item_id}/approve")
    async def approve_content(item_id: str, user: dict = Depends(get_current_user)):
        require_privileged(user)
        await _get_item(user["company_id"], item_id)
        await db.mkt_content.update_one({"id": item_id, "company_id": user["company_id"]},
                                        {"$set": {"status": "approved", "updated_at": _now_iso()}})
        return await _get_item(user["company_id"], item_id)

    class ScheduleBody(BaseModel):
        scheduled_at: str

    @api.post("/marketing/content/{item_id}/schedule")
    async def schedule_content(item_id: str, body: ScheduleBody, user: dict = Depends(get_current_user)):
        require_privileged(user)
        await _get_item(user["company_id"], item_id)
        await db.mkt_content.update_one({"id": item_id, "company_id": user["company_id"]},
                                        {"$set": {"status": "scheduled", "scheduled_at": body.scheduled_at, "updated_at": _now_iso()}})
        return await _get_item(user["company_id"], item_id)

    @api.post("/marketing/content/{item_id}/publish")
    async def publish_content(item_id: str, user: dict = Depends(get_current_user)):
        """Manual publish (human in control). Fires the configured n8n/Make webhook.
        Native platform OAuth publishers can be plugged in here later without changing callers."""
        require_privileged(user)
        item = await _get_item(user["company_id"], item_id)
        brand = await get_brand(user["company_id"])
        webhook = (brand.get("publish_webhook_url") or "").strip()
        delivery = {"webhook_configured": bool(webhook), "webhook_status": None}
        if webhook:
            payload = {"event": "publish", "brand": brand.get("company_name"),
                       "channel": item.get("channel"), "title": item.get("title"),
                       "body": item.get("body"), "hashtags": item.get("hashtags"),
                       "cta": item.get("cta"), "image_url": item.get("image_url"),
                       "seo": item.get("seo"), "content_id": item.get("id")}
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    r = await client.post(webhook, json=payload)
                    delivery["webhook_status"] = r.status_code
            except Exception as e:
                logger.warning("Publish webhook failed: %s", e)
                delivery["webhook_status"] = "error"
        await db.mkt_content.update_one({"id": item_id, "company_id": user["company_id"]},
                                        {"$set": {"status": "published", "published_at": _now_iso(), "updated_at": _now_iso()}})
        result = await _get_item(user["company_id"], item_id)
        result["_delivery"] = delivery
        return result

    # ------------------------------ Image gen ---------------------------------
    class ImageBody(BaseModel):
        prompt: Optional[str] = None

    @api.post("/marketing/content/{item_id}/image")
    async def generate_image(item_id: str, body: ImageBody, user: dict = Depends(get_current_user)):
        require_privileged(user)
        item = await _get_item(user["company_id"], item_id)
        brand = await get_brand(user["company_id"])
        colors = ", ".join(brand.get("brand_colors") or [])
        base_prompt = (body.prompt or item.get("image_prompt") or item.get("title") or "brand marketing visual")
        prompt = (f"{base_prompt}. Clean modern branded marketing visual for {brand.get('company_name')} "
                  f"({brand.get('industry')}). Brand colors: {colors}. High quality, no text artifacts.")
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"mkt-img-{uuid.uuid4()}",
                       system_message="You are a brand visual generator.").with_model(
                           "gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
        _text, images = await chat.send_message_multimodal_response(UserMessage(text=prompt))
        if not images:
            raise HTTPException(status_code=502, detail="Generazione immagine non riuscita, riprova.")
        img = images[0]
        media_id = str(uuid.uuid4())
        await db.mkt_media.insert_one({
            "id": media_id, "company_id": user["company_id"], "content_id": item_id,
            "mime_type": img.get("mime_type", "image/png"), "data": img["data"],
            "created_at": _now_iso(),
        })
        image_url = f"/api/marketing/media/{media_id}"
        await db.mkt_content.update_one({"id": item_id, "company_id": user["company_id"]},
                                        {"$set": {"image_url": image_url, "updated_at": _now_iso()}})
        return {"image_url": image_url}

    @api.get("/marketing/media/{media_id}")
    async def serve_media(media_id: str):
        doc = await db.mkt_media.find_one({"id": media_id}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Media non trovato")
        return Response(content=base64.b64decode(doc["data"]), media_type=doc.get("mime_type", "image/png"))

    logger.info("Marketing agent module ready (%d channels, %d categories)", len(CHANNELS), len(CATEGORIES))
    return {"get_brand": get_brand}
