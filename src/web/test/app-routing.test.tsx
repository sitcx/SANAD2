import { QueryClient } from "@tanstack/react-query";
import { createRouter, rootRouteId } from "@tanstack/react-router";
import { describe, expect, it } from "vitest";

import { routeTree } from "@/routeTree.gen";
import { Route as loginRoute } from '@/routes/login';

// Match routes without running loaders or rendering: loaders may need a server or
// network the test run lacks, and jsdom never loads the stylesheets React waits on.
describe("App routing", () => {
  it('opens the sign-up form from explicit sign-up search state', () => {
    const validate = loginRoute.options.validateSearch;
    if (typeof validate !== 'function') throw new Error('Missing login search validator');
    expect(validate({ mode: 'signup' })).toEqual({ mode: 'signup' });
    expect(validate({ mode: 'unknown' })).toEqual({ mode: undefined });
  });
  it("matches a page for / instead of falling back to not found", () => {
    const router = createRouter({ routeTree, context: { queryClient: new QueryClient() } });

    const matches = router.matchRoutes("/");

    expect(matches.at(-1)?.routeId).not.toBe(rootRouteId);
  });
  it('opens job details independently of the job list screen', () => {
    const router = createRouter({ routeTree, context: { queryClient: new QueryClient() } });
    const matches = router.matchRoutes('/jobs/analyst');
    expect(matches.at(-1)?.routeId).toBe('/jobs_/$jobId');
    expect(matches.some(match => match.routeId === '/jobs')).toBe(false);
  });
  it('provides separate application tracking and simulated sign-in screens', () => {
    const router = createRouter({ routeTree, context: { queryClient: new QueryClient() } });
    expect(router.matchRoutes('/applications').at(-1)?.routeId).toBe('/applications');
    expect(router.matchRoutes('/login').at(-1)?.routeId).toBe('/login');
    expect(router.matchRoutes('/charter').at(-1)?.routeId).toBe('/charter');
  });
});
