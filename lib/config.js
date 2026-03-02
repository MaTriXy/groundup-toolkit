"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.config = exports.TOOLKIT_ROOT = void 0;

exports.TOOLKIT_ROOT = "/root/.openclaw";

exports.config = {
    assistant: {
        name: "Christina",
        email: "christina@groundup.vc"
    },
    team: {
        members: [
            { name: "Navot Volk", email: "navot@groundup.vc", phone: "+972546611106" },
            { name: "Jordan Odinsky", email: "jordan@groundup.vc", phone: "+15165091544" },
            { name: "Cory Hymel", email: "cory@groundup.vc", phone: "+13109240006" },
            { name: "David Stark", email: "david@groundup.vc", phone: "+972586336427" },
            { name: "Allie", email: "allie@groundup.vc", phone: "+972586589921" }
        ]
    },
    // Also export flat teamMembers for backward compat with christina-scheduler
    teamMembers: [
        { name: "Navot Volk", email: "navot@groundup.vc", hubspotOwnerId: "76836577", phoneNumber: "+972546611106" },
        { name: "Jordan Odinsky", email: "jordan@groundup.vc", hubspotOwnerId: "7042119", phoneNumber: "+15165091544" },
        { name: "Cory Hymel", email: "cory@groundup.vc", hubspotOwnerId: "80040886", phoneNumber: "+13109240006" },
        { name: "David Stark", email: "david@groundup.vc", hubspotOwnerId: "78681903", phoneNumber: "+972586336427" },
        { name: "Allie", email: "allie@groundup.vc", hubspotOwnerId: "80351816", phoneNumber: "+972586589921" }
    ],
    christinaEmail: "christina@groundup.vc",
    groundupDomain: "@groundup.vc",
    gogKeyringPassword: process.env.GOG_KEYRING_PASSWORD || "openclaw-gog-key",
    anthropicApiKey: process.env.ANTHROPIC_API_KEY || "",
    matonApiKey: process.env.MATON_API_KEY || "",
    whatsappAccount: process.env.WHATSAPP_ACCOUNT || "main"
};
