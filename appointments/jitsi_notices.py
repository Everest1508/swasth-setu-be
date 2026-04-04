"""Localized Jitsi onboarding copy for API responses (matches app languages: en, hi, mr, pa)."""

JITSI_VIDEO_NOTICES = {
    "en": (
        "Video consultations use Jitsi Meet in the browser or the Jitsi Meet app. "
        "Create a free Jitsi account and install the Jitsi Meet app on your phone "
        "for the most reliable experience."
    ),
    "hi": (
        "वीडियो परामर्श ब्राउज़र में या Jitsi Meet ऐप के ज़रिए होते हैं। "
        "निःशुल्क Jitsi खाता बनाएँ और अपने फ़ोन पर Jitsi Meet ऐप इंस्टॉल करें — "
        "सबसे भरोसेमंद अनुभव के लिए।"
    ),
    "mr": (
        "व्हिडिओ सल्लामसलत ब्राउझरमध्ये किंवा Jitsi Meet अॅपद्वारे होते. "
        "विनामूल्य Jitsi खाते तयार करा आणि आपल्या फोनवर Jitsi Meet अॅप इंस्टॉल करा — "
        "सर्वात विश्वासार्ह अनुभवासाठी."
    ),
    "pa": (
        "ਵੀਡੀਓ ਸਲਾਹ ਬ੍ਰਾਊਜ਼ਰ ਵਿੱਚ ਜਾਂ Jitsi Meet ਐਪ ਰਾਹੀਂ ਹੁੰਦੀ ਹੈ। "
        "ਮੁਫ਼ਤ Jitsi ਖਾਤਾ ਬਣਾਓ ਅਤੇ ਆਪਣੇ ਫੋਨ ਤੇ Jitsi Meet ਐਪ ਇੰਸਟਾਲ ਕਰੋ — "
        "ਸਭ ਤੋਂ ਭਰੋਸੇਮੰਦ ਅਨੁਭਵ ਲਈ।"
    ),
}

_SUPPORTED = frozenset(JITSI_VIDEO_NOTICES.keys())


def resolve_request_language(request):
    """Pick en/hi/mr/pa from query param, then Accept-Language, else en."""
    if request is None:
        return "en"

    qp = getattr(request, "query_params", None)
    q = None
    if qp is not None:
        q = qp.get("lang") or qp.get("language")
    if not q and hasattr(request, "GET"):
        q = request.GET.get("lang") or request.GET.get("language")
    if q:
        primary = str(q).strip().lower().split("-")[0]
        if primary in _SUPPORTED:
            return primary

    accept = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
    if accept:
        for part in accept.split(","):
            token = part.split(";")[0].strip().lower()
            if not token:
                continue
            primary = token.split("-")[0]
            if primary in _SUPPORTED:
                return primary

    return "en"


def get_jitsi_video_notice_for_request(request):
    lang = resolve_request_language(request)
    return JITSI_VIDEO_NOTICES.get(lang, JITSI_VIDEO_NOTICES["en"])
