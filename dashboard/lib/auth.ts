import NextAuth from "next-auth"
import Google from "next-auth/providers/google"

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    authorized({ auth }) {
      return !!auth
    },
    signIn({ profile }) {
      // Only allow @groundup.vc emails
      return profile?.email?.endsWith("@groundup.vc") ?? false
    },
    session({ session }) {
      return session
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
  session: {
    strategy: "jwt",
    maxAge: 7 * 24 * 60 * 60, // Security: 7 day session expiry (default was 30 days)
  },
})
