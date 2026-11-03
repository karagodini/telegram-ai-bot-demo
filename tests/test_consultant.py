from __future__ import annotations

from collections.abc import Sequence

from bot.knowledge.faq import FaqIndex
from bot.memory import DialogMemory
from bot.providers.base import ChatMessage, ProviderError
from bot.providers.fallback import FallbackProvider
from bot.providers.stub import StubProvider
from bot.services.consultant import Consultant

FAQ = """
## Доставка
keywords: доставка

Доставка по городу занимает один день.
"""


class _Down:
    name = "down"

    async def complete(self, messages: Sequence[ChatMessage]) -> str:
        raise ProviderError("timeout")


class _Capture:
    name = "capture"

    def __init__(self) -> None:
        self.seen: list[list[ChatMessage]] = []

    async def complete(self, messages: Sequence[ChatMessage]) -> str:
        self.seen.append(list(messages))
        return "Готовый ответ"


async def test_fallback_uses_stub_when_api_fails() -> None:
    stub = StubProvider(FaqIndex.from_markdown(FAQ), min_score=0.1)
    provider = FallbackProvider(_Down(), stub)
    answer = await provider.complete([{"role": "user", "content": "Расскажи про доставку"}])
    assert provider.name == "down+fallback:stub"
    assert "один день" in answer


async def test_consultant_sends_prompt_and_stores_history() -> None:
    faq = FaqIndex.from_markdown(FAQ)
    memory = DialogMemory(max_messages=4)
    capture = _Capture()
    consultant = Consultant(
        provider=capture,
        faq=faq,
        memory=memory,
        system_prompt="Ты консультант студии.",
    )

    first = await consultant.reply(7, "Как устроена доставка?")
    await consultant.reply(7, "А если за город?")

    assert first == "Готовый ответ"
    second_request = capture.seen[1]
    assert second_request[0]["role"] == "system"
    assert "Ты консультант студии." in second_request[0]["content"]
    assert "Доставка по городу" in second_request[0]["content"]
    assert second_request[-1] == {"role": "user", "content": "А если за город?"}
    assert any(item["content"] == "Как устроена доставка?" for item in second_request)
    assert [item["role"] for item in memory.get(7)] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]


def test_memory_trims_and_isolates_chats() -> None:
    memory = DialogMemory(max_messages=2)
    memory.add(1, "user", "раз")
    memory.add(1, "assistant", "два")
    memory.add(1, "user", "три")
    memory.add(2, "user", "другой чат")

    assert [item["content"] for item in memory.get(1)] == ["два", "три"]
    assert memory.get(2)[0]["content"] == "другой чат"
    memory.reset(2)
    assert memory.get(2) == []
    assert memory.get(1)
