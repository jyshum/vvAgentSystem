import { measuringCount } from "@/lib/derive";

interface QueryError {
  message: string;
}

interface QueryResult<T> {
  data: T[] | null;
  error: QueryError | null;
}

interface OpenAuditCard {
  id: string;
  created_at: string;
}

interface VerifiedAuditCard {
  id: string;
  status: string;
  created_at: string;
  applied_at: string | null;
}

export function mapBoardAuditCardResults({
  openCardsResult,
  verifiedCardsResult,
  latestTrackerRanAt,
  nowMs = Date.now(),
}: {
  openCardsResult: QueryResult<OpenAuditCard>;
  verifiedCardsResult: QueryResult<VerifiedAuditCard>;
  latestTrackerRanAt: string | null;
  nowMs?: number;
}) {
  if (openCardsResult.error) {
    throw new Error(
      `Unable to load board audit cards (open cards): ${openCardsResult.error.message}`,
    );
  }
  if (verifiedCardsResult.error) {
    throw new Error(
      `Unable to load board audit cards (verified cards): ${verifiedCardsResult.error.message}`,
    );
  }

  const openCards = openCardsResult.data ?? [];
  const verifiedCards = verifiedCardsResult.data ?? [];

  for (const card of verifiedCards) {
    if (!card.applied_at) {
      throw new Error(
        `Verified technical audit action card ${card.id} is missing applied_at`,
      );
    }
  }

  const oldestOpenDays = openCards.length
    ? Math.floor(
        (nowMs -
          Math.min(...openCards.map((card) => new Date(card.created_at).getTime()))) /
          86400000,
      )
    : null;

  return {
    openCount: openCards.length,
    oldestOpenDays,
    measuring: measuringCount(
      verifiedCards.map((card) => ({
        status: "implemented",
        created_at: card.applied_at as string,
      })),
      latestTrackerRanAt,
    ),
  };
}
