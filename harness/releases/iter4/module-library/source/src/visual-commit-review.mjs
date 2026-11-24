

export function visualCommitReview({frameCount,inspected,alreadyReviewed,moduleId,source,sourceAvailable=false}) {
 if (!moduleId || frameCount <= 4 || inspected || alreadyReviewed) return {status:'allow'};
 const note=sourceAvailable
   ? 'The proposed answer has NOT been submitted. The original overview is temporally sparse and no question-directed inspection has executed. Your next call should be consult_capability_path with moduleId '+moduleId+' and input {mode:"acquire_public_video",source:"'+source+'",startSeconds:...,endSeconds:...,maxFrameGap:...,reason:"visible scope and unresolved transition"}. Determine the interval from the visible subsection and PUBLIC_SOURCE_ACQUISITION timestamps; inspect the requested subsection rather than a later recap. The module permits up to 96 frames: choose a narrow interval and adequate temporal density. Read its actual returned chronological frames, and use the second call if a completion/reset boundary remains ambiguous. Then submit the evidence-based answer. This is not correctness feedback and supplies no count or answer.'
   : 'The proposed answer has not been submitted. The delivered sequence has not had a question-directed inspection. Use consult_capability_path with this moduleId and input {mode:"inspect_public_sequence",source,frameIndices:[relevant zero-based indices]} to compare the target event and its context. This is a one-time evidence review, not correctness feedback. No new frames or labels are available. If inspection cannot resolve the uncertainty, keep it uncertain and submit your best native answer. No answer is substituted.';
 return {status:'review_once',moduleId,source,noWorldActionExecuted:true,note};
}
