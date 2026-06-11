import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent import CommentAgent
from app.schemas import InstagramComment


async def main():
    agent = CommentAgent()
    samples = [
        InstagramComment(id="c1", text="What is the price?", username="alice"),
        InstagramComment(id="c2", text="Great post!", username="bob"),
        InstagramComment(id="c3", text="Free crypto giveaway http://spam.test", username="bot"),
        InstagramComment(id="c4", text="roast me a little", username="tester4"),
    ]
    for sample in samples:
        decision = await agent.decide(sample)
        print(sample.text, "=>", decision.action, decision.category, decision.confidence)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
