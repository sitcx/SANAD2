import { coachQuestions } from './sanad-data';

export type TrainingProgress = Record<string, number[]>;

export function getTrainingReadiness(completedQuestions: readonly number[] = []): number {
  const completed = new Set(completedQuestions.filter(index => Number.isInteger(index) && index >= 0 && index < coachQuestions.length));
  return Math.round(completed.size / coachQuestions.length * 100);
}

export function recordTrainingQuestion(progress: TrainingProgress, jobId: string, questionIndex: number): TrainingProgress {
  if (!Number.isInteger(questionIndex) || questionIndex < 0 || questionIndex >= coachQuestions.length) return progress;
  const completed = progress[jobId] ?? [];
  if (completed.includes(questionIndex)) return progress;
  return { ...progress, [jobId]: [...completed, questionIndex] };
}