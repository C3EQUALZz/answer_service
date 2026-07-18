from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class TaskIQConfig:
    """Behaviour of the taskiq broker, independent of where it connects.

    Split from :class:`NatsConfig` and :class:`RedisConfig` on purpose: those
    say *where* the broker talks, this says *how* it behaves. Retry policy and
    stream naming change far more often than connection details, and they change
    per environment rather than per deployment target.

    Attributes:
        subject: JetStream subject tasks are published to.
        stream_name: JetStream stream that persists the task messages.
        durable: Durable consumer name, so a restarted worker resumes its queue.
        queue: Queue group name, letting replicas share one work queue.
        result_ex_time: Seconds a task result is kept in Redis.
        default_retry_count: Attempts before a failing task is given up on.
        default_delay: Seconds before the first retry.
        use_jitter: Whether to spread retries randomly, so replicas that failed
            together do not retry in lockstep.
        use_delay_exponent: Whether the delay grows exponentially per attempt.
        max_delay_exponent: Ceiling on the exponential delay, in seconds.
    """

    subject: str = "answer_service.tasks"
    stream_name: str = "answer_service_jetstream"
    durable: str = "answer_service_durable"
    queue: str = "answer_service_workers"
    result_ex_time: int = 1000
    default_retry_count: int = 3
    default_delay: float = 5.0
    use_jitter: bool = True
    use_delay_exponent: bool = True
    max_delay_exponent: float = 60.0
