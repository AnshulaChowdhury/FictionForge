#!/usr/bin/env python3
"""
Script to check Redis queue for pending Arq jobs.

Run this from the project root to see if embedding jobs are queued:
    python scripts/check_redis_queue.py
"""
import asyncio
import redis.asyncio as redis
from arq.connections import RedisSettings


async def check_queue():
    """Check Redis for queued Arq jobs."""
    # Connect to Redis
    settings = RedisSettings.from_dsn("redis://localhost:6379")
    client = await redis.Redis(
        host=settings.host,
        port=settings.port,
        db=settings.database
    )

    print("=" * 60)
    print("CHECKING ARQ QUEUE STATUS")
    print("=" * 60)

    # Check queued jobs
    queued_jobs = await client.llen('arq:queue')
    print(f"\n📊 Queued Jobs: {queued_jobs}")

    # Check in-progress jobs
    in_progress = await client.hlen('arq:in-progress')
    print(f"⏳ In Progress: {in_progress}")

    # Get all keys related to Arq
    arq_keys = await client.keys('arq:*')
    print(f"\n🔑 Total Arq Keys: {len(arq_keys)}")

    # Show some recent job IDs
    if queued_jobs > 0:
        print("\n📋 Queued Job IDs:")
        job_ids = await client.lrange('arq:queue', 0, 9)  # First 10
        for idx, job_id in enumerate(job_ids, 1):
            print(f"  {idx}. {job_id.decode()}")

    # Check for job results
    result_keys = [k for k in arq_keys if b'result' in k]
    if result_keys:
        print(f"\n✅ Completed Jobs (with results): {len(result_keys)}")
        for key in result_keys[:5]:  # Show first 5
            result = await client.get(key)
            print(f"  - {key.decode()}: {result.decode() if result else 'N/A'}")

    await client.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(check_queue())
