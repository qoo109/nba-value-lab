"use strict";

(function () {
  const v5 = window.NBAVL.v5;

  function eventTime(record) {
    return record.price_evaluated_at || record.evaluation_cutoff || record.predicted_at || record.observed_at || "";
  }

  function entityKey(record) {
    return [record.game_id, record.selection_team_id || record.target].filter(Boolean).join("::")
      || record.prediction_id || record.price_evaluation_id || "unknown";
  }

  function evaluationKey(record) {
    return record.price_evaluation_id || [entityKey(record), eventTime(record), record.target_odds].join("::");
  }

  function numeric(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function latestResolvedMainRecords(records) {
    const latest = new Map();
    records
      .filter((record) => record.main_candidate && typeof record.won === "boolean")
      .sort((a, b) => eventTime(a).localeCompare(eventTime(b)))
      .forEach((record) => latest.set(entityKey(record), record));
    return [...latest.values()].sort((a, b) => eventTime(a).localeCompare(eventTime(b)));
  }

  function uniqueEvaluations(records) {
    const unique = new Map();
    records
      .slice()
      .sort((a, b) => eventTime(a).localeCompare(eventTime(b)))
      .forEach((record) => unique.set(evaluationKey(record), record));
    return [...unique.values()];
  }

  function groupEvaluations(records) {
    const groups = new Map();
    uniqueEvaluations(records).forEach((record) => {
      const key = entityKey(record);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(record);
    });
    return [...groups.entries()]
      .map(([key, items]) => ({ key, records: items.sort((a, b) => eventTime(a).localeCompare(eventTime(b))) }))
      .sort((a, b) => eventTime(b.records.at(-1)).localeCompare(eventTime(a.records.at(-1))));
  }

  function values(records, field) {
    return records.map((record) => numeric(record[field])).filter((value) => value !== null);
  }

  function cumulativeEquity(records) {
    let total = 0;
    const series = [0];
    latestResolvedMainRecords(records).forEach((record) => {
      const odds = numeric(record.target_odds);
      if (odds === null || odds <= 1) return;
      total += record.won ? odds - 1 : -1;
      series.push(total);
    });
    return series;
  }

  function cumulativeHitRate(records) {
    let wins = 0;
    return latestResolvedMainRecords(records).map((record, index) => {
      if (record.won) wins += 1;
      return wins / (index + 1);
    });
  }

  v5.modules.history = {
    eventTime,
    entityKey,
    evaluationKey,
    numeric,
    latestResolvedMainRecords,
    uniqueEvaluations,
    groupEvaluations,
    values,
    cumulativeEquity,
    cumulativeHitRate,
  };
}());
