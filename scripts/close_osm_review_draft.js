function parseReviewSource(body) {
  const marker = /^<!-- osm-review-source:({.*}) -->$/m;
  const match = body.match(marker);
  if (!match) return null;

  let source;
  try {
    source = JSON.parse(match[1]);
  } catch {
    return null;
  }
  const expectedKeys = [
    "issueNumber",
    "reviewBranch",
    "reviewPullRequestNumber",
    "schemaVersion",
  ];
  if (
    Object.keys(source).sort().join(",") !== expectedKeys.join(",") ||
    source.schemaVersion !== 1 ||
    !Number.isSafeInteger(source.issueNumber) || source.issueNumber < 1 ||
    !Number.isSafeInteger(source.reviewPullRequestNumber) || source.reviewPullRequestNumber < 1 ||
    !/^automation\/osm-review-[0-9]+$/.test(source.reviewBranch)
  ) {
    return null;
  }
  return source;
}

async function closeRecordedDraftReview({ body, baseRef, owner, repo, github, core }) {
  const pullRequestBody = body || "";
  const source = parseReviewSource(pullRequestBody);
  if (!source) {
    const message = "OSM review source marker has an unsupported shape; nothing to close.";
    if (pullRequestBody.includes("<!-- osm-review-source:")) {
      core.warning(message);
    } else {
      core.info("No OSM review source marker; nothing to close.");
    }
    return;
  }

  const { data: pull } = await github.rest.pulls.get({
    owner,
    repo,
    pull_number: source.reviewPullRequestNumber,
  });
  if (
    pull.state !== "open" ||
    !pull.draft ||
    pull.head.ref !== source.reviewBranch ||
    pull.base.ref !== baseRef
  ) {
    core.info(`Recorded draft review PR #${source.reviewPullRequestNumber} is not an open matching draft.`);
    return;
  }

  await github.rest.pulls.update({
    owner,
    repo,
    pull_number: source.reviewPullRequestNumber,
    state: "closed",
  });
  core.info(`Closed draft review PR #${source.reviewPullRequestNumber}.`);
}

module.exports = { closeRecordedDraftReview, parseReviewSource };
