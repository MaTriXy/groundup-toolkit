export { auth as middleware } from "@/lib/auth"

export const config = {
  matcher: [
    // Protect pages (not API routes — they handle auth themselves)
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
}
