from pydantic import BaseModel, computed_field
from typing import Any
from markdownify import markdownify as md


class AppFamily(BaseModel):
    id: int
    type: str
    version: str
    major_version: str


class BlockContent(BaseModel):
    type: str
    content_html: str
    settings: dict[str, Any]

    @computed_field
    @property
    def content_markdown(self) -> str:
        return md(self.content_html, heading_style="ATX")


class EpicDocument(BaseModel):
    id: int
    hash_id: str
    revision_hash_id: str
    revision_id: int
    updated_at: str
    slug: str
    title: str
    description: str
    source: str
    locale: str
    document_type: str | None
    seo_title: str
    seo_description: str | None
    seo_slug: str
    readiness: str
    entitlement: str
    views_count: int
    application_families: list[str]
    blocks: list[BlockContent]
    applications: list[AppFamily]
    tags: list
    prereq_documents: list
    related_documents: list


class SearchItem(BaseModel):
    title: str
    url: str
    excerpt: str
    published_at: str
    path: str
    application_families: list[str]
    item_types: list[str]


class SearchResponse(BaseModel):
    total_count: int
    data: list[SearchItem]
