import { describe, expect, it } from 'vitest';
import { dailySkills, nextDailySkillIndex } from '@/lib/daily-skills';

describe('Daily career skill rotation', () => {
  it('moves to a different skill on every request', () => {
    expect(dailySkills.length).toBeGreaterThan(1);
    for (let index = 0; index < dailySkills.length; index++) {
      expect(dailySkills[nextDailySkillIndex(index)]?.id).not.toBe(dailySkills[index]?.id);
    }
  });

  it('visits the entire fixed collection before returning to the first skill', () => {
    let index = 0;
    const visited = new Set<string>();
    for (let count = 0; count < dailySkills.length; count++) {
      const skill = dailySkills[index];
      if (!skill) throw new Error('Rotation selected a missing skill');
      visited.add(skill.id);
      index = nextDailySkillIndex(index);
    }
    expect(visited.size).toBe(dailySkills.length);
    expect(index).toBe(0);
  });
});