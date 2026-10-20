import hashlib
import re
from dataclasses import dataclass

from app.config.constants import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    MAX_CHUNKS_PER_DOC,
    MIN_CHUNK_SIZE,
)
from app.config.logging import get_logger
from app.config.settings import get_settings
from app.processing.section_detector import DocumentSection

logger = get_logger(__name__)


def tokenize(text: str) -> list[str]:
    """Return stable whitespace/punctuation tokens for chunk sizing.

    This keeps chunking deterministic without adding another tokenizer dependency.
    The same tokenizer is used when persisting ``token_count``.
    """
    return re.findall(r"\w+(?:['’-]\w+)*|[^\w\s]", text, flags=re.UNICODE)


def detokenize(tokens: list[str]) -> str:
    text = ""
    for token in tokens:
        if text and re.match(r"[\w'’-]", token) and re.search(r"[\w'’-]$", text):
            text += " "
        text += token
    return text.strip()


@dataclass
class TextChunk:
    text: str
    chunk_index: int
    start_char: int
    end_char: int
    start_page: int
    end_page: int
    section_title: str | None = None
    section_level: int | None = None
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        self.hash = hashlib.sha256(self.text.encode()).hexdigest()[:16]


class Chunker:
    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        min_chunk_size: int = MIN_CHUNK_SIZE,
        max_chunks: int = MAX_CHUNKS_PER_DOC,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunks = max_chunks

    def chunk_text(
        self,
        text: str,
        start_page: int = 1,
        end_page: int = 1,
        section_title: str | None = None,
        section_level: int | None = None,
    ) -> list[TextChunk]:
        tokens = tokenize(text or "")
        if not tokens:
            return []

        chunks = []
        chunk_index = 0
        start = 0
        token_count = len(tokens)

        while start < token_count and chunk_index < self.max_chunks:
            end = min(start + self.chunk_size, token_count)
            chunk_tokens = tokens[start:end]
            chunk_text = detokenize(chunk_tokens)

            if chunk_tokens:
                chunk = TextChunk(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    start_char=0,
                    end_char=len(chunk_text),
                    start_page=start_page,
                    end_page=end_page,
                    section_title=section_title,
                    section_level=section_level,
                )
                chunks.append(chunk)
                chunk_index += 1

            if end == token_count:
                break

            start = end - self.chunk_overlap
            start = max(start, 0)

        logger.debug(
            "text_chunked",
            total_chunks=len(chunks),
            chunk_size=self.chunk_size,
            overlap=self.chunk_overlap,
        )

        return chunks

    def chunk_sections(self, sections: list[DocumentSection]) -> list[TextChunk]:
        all_chunks = []

        for section in sections:
            section_chunks = self.chunk_text(
                text=section.content,
                start_page=section.start_page,
                end_page=section.end_page,
                section_title=section.title,
                section_level=section.level,
            )
            all_chunks.extend(section_chunks)

            if section.subsections:
                sub_chunks = self.chunk_sections(section.subsections)
                all_chunks.extend(sub_chunks)

        self._reindex_chunks(all_chunks)
        return all_chunks[: self.max_chunks]

    def _reindex_chunks(self, chunks: list[TextChunk]) -> None:
        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i


class SemanticChunker(Chunker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sentence_endings = {".", "!", "?", "\n\n"}

    def chunk_text(
        self,
        text: str,
        start_page: int = 1,
        end_page: int = 1,
        section_title: str | None = None,
        section_level: int | None = None,
    ) -> list[TextChunk]:
        if not text or len(text.strip()) < self.min_chunk_size:
            return []

        sentences = self._split_sentences(text)
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_index = 0
        char_offset = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            if current_length + sentence_len > self.chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                chunk = TextChunk(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    start_char=char_offset - current_length,
                    end_char=char_offset,
                    start_page=start_page,
                    end_page=end_page,
                    section_title=section_title,
                    section_level=section_level,
                )
                chunks.append(chunk)
                chunk_index += 1

                if chunk_index >= self.max_chunks:
                    break

                overlap_sentences = self._get_overlap_sentences(current_chunk)
                current_chunk = overlap_sentences
                current_length = sum(len(s) for s in overlap_sentences)
                char_offset -= sum(len(s) for s in current_chunk[: -len(overlap_sentences)])

            current_chunk.append(sentence)
            current_length += sentence_len
            char_offset += sentence_len + 1

        if current_chunk and chunk_index < self.max_chunks:
            chunk_text = " ".join(current_chunk)
            chunk = TextChunk(
                text=chunk_text,
                chunk_index=chunk_index,
                start_char=char_offset - current_length,
                end_char=char_offset,
                start_page=start_page,
                end_page=end_page,
                section_title=section_title,
                section_level=section_level,
            )
            chunks.append(chunk)

        self._reindex_chunks(chunks)
        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        import re

        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

    def _get_overlap_sentences(self, sentences: list[str]) -> list[str]:
        overlap_chars = 0
        overlap = []

        for sentence in reversed(sentences):
            if overlap_chars + len(sentence) <= self.chunk_overlap:
                overlap.insert(0, sentence)
                overlap_chars += len(sentence) + 1
            else:
                break

        return overlap


def create_chunker(strategy: str = "fixed", **kwargs) -> Chunker:
    settings = get_settings()

    chunk_size = kwargs.get("chunk_size", settings.CHUNK_SIZE)
    chunk_overlap = kwargs.get("chunk_overlap", settings.CHUNK_OVERLAP)

    if strategy == "semantic":
        return SemanticChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    else:
        return Chunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)


def chunk_document(
    text: str, pages: list[str] = None, strategy: str = "fixed", **kwargs
) -> list[TextChunk]:
    chunker = create_chunker(strategy, **kwargs)

    if pages:
        all_chunks: list[TextChunk] = []
        for page_number, page in enumerate(pages, start=1):
            page_chunks = chunker.chunk_text(
                page,
                start_page=page_number,
                end_page=page_number,
            )
            all_chunks.extend(page_chunks)
        chunker._reindex_chunks(all_chunks)
        return all_chunks[: chunker.max_chunks]

    return chunker.chunk_text(text)
