export { auth as middleware } from "@/lib/auth"

export const config = {
  matcher: [
    // Protect everything except auth routes, Next.js internals, and static files
    "/((?!api/auth|_next/static|_next/image|favicon.ico).*)",
  ],
}
