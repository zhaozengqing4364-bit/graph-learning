import type { ReviewItem } from '../types'

type ReviewIdentity = Pick<ReviewItem, 'review_id' | 'node_id' | 'topic_id' | 'node_name'>

export function resolveReviewNodeTitle(
  reviewDetail: ReviewIdentity,
  reviewList: ReviewIdentity[],
): string {
  const detailName = reviewDetail.node_name?.trim()
  if (detailName) {
    return detailName
  }

  const queuedName = reviewList.find((item) => item.review_id === reviewDetail.review_id)?.node_name?.trim()
  if (queuedName) {
    return queuedName
  }

  return reviewDetail.node_id
}
