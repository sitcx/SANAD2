import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  useLocation,
  HeadContent,
  Scripts,
  type ErrorComponentProps,
} from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";

import appCss from "../styles.css?url";
import { reportAppError } from "../lib/error-reporting";
import { SiteHeader } from '@/components/sanad-layout';
import { SanadProvider } from '@/lib/sanad-context';
import { Button } from '@/components/ui/button';
import { PlatformGuide } from '@/components/platform-guide';
import { TooltipProvider } from '@/components/ui/tooltip';

function NotFoundComponent() {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-background px-4" dir="rtl">
      <div className="max-w-md text-center">
        <h1 className="text-7xl font-bold text-foreground">404</h1>
        <h2 className="mt-4 text-xl font-semibold text-foreground">الصفحة غير موجودة</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          لم نجد الصفحة المطلوبة. لنعد إلى بداية رحلتك.
        </p>
        <div className="mt-6">
          <Button asChild><Link to="/">العودة إلى الرئيسية</Link></Button>
        </div>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: ErrorComponentProps) {
  console.error(error);
  const router = useRouter();
  useEffect(() => {
    reportAppError(error, { boundary: "tanstack_root_error_component" });
  }, [error]);

  return (
    <div className="flex min-h-dvh items-center justify-center bg-background px-4" dir="rtl">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold tracking-tight text-foreground">
          تعذّر تحميل الصفحة
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          حدث خطأ غير متوقع. يمكنك المحاولة مجددًا أو العودة إلى الرئيسية.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <Button
            onClick={() => {
              router.invalidate();
              reset();
            }}
          >
            حاول مجددًا
          </Button>
          <Button asChild variant="outline"><a href="/">العودة إلى الرئيسية</a></Button>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    // Replace these placeholders with the app's name and description when first building the app.
    // Each content route, / included, must still set its own head(). Never add og:image or
    // twitter:image here: every page without its own would inherit the root's preview image.
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "سَند — كفاءتك أولًا" },
      { name: "description", content: "سَند، رفيقك الذكي لمقابلة وظيفية أكثر وضوحًا وعدلًا." },
      { name: "author", content: "سَند" },
      { property: "og:title", content: "سَند — كفاءتك أولًا" },
      { property: "og:description", content: "وكيل ذكي يجهّز المرشح والشركة ويدعم التواصل في المقابلة الوظيفية." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
    links: [
      {
        rel: "stylesheet",
        href: appCss,
      },
      { rel: "icon", href: "/favicon.png?v=sanad-emblem-2", type: "image/png" },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" },
      { rel: "stylesheet", href: "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;450;500;600;700&display=swap" },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  const { pathname } = useLocation();
  const bare = pathname === '/login';

  return (
    <QueryClientProvider client={queryClient}>
      <SanadProvider>
        <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-background focus:p-3">انتقل إلى المحتوى</a>
        <TooltipProvider delayDuration={200}>{!bare && <SiteHeader />}
        <main id="main-content"><Outlet /></main>
        <PlatformGuide /></TooltipProvider>
      </SanadProvider>
    </QueryClientProvider>
  );
}
