"""Training material for the cleaning models.

Everything a model learns from is either labeled examples written for it (below) or real sentences taken
from the stored transcripts. Nothing has to be reviewed by hand.
"""

from app.cleaning import rules
from app.cleaning.ml import words_of

LOW_CONFIDENCE = 0.6
MIN_CONTENT_WORDS = 5   # a real content sentence needs at least this many words
MAX_BASE_WORDS = 40

# Redundant sentences, in six kinds. These are the labeled examples of the sentence model.
FAMILIES: dict[str, list[str]] = {
    "Subscribe / like requests": [
        "Please like and subscribe to the channel.",
        "Don't forget to subscribe and hit the notification bell.",
        "If you enjoyed this video, smash that like button.",
        "Subscribe for more videos like this one.",
        "Make sure you subscribe so you never miss an upload.",
        "Hit the subscribe button and turn on notifications.",
        "Consider subscribing if you want to see more content like this.",
        "Click the bell icon to get notified of new videos.",
        "Like, share and subscribe, it really helps the channel.",
        "If you're new here, welcome, and please subscribe.",
        "Give this video a thumbs up before you go.",
        "Join the channel by hitting subscribe right now.",
    ],
    "Thank-you and goodbye": [
        "Thanks for watching and I'll see you in the next video.",
        "That's all for today, see you next time.",
        "Thank you so much for watching, take care.",
        "I hope you enjoyed this video and I'll see you soon.",
        "Until next time, goodbye everyone.",
        "Thanks for joining me today, bye for now.",
        "See you in the next one.",
        "That brings us to the end of today's video.",
        "Stay curious and I'll catch you later.",
        "Thank you for being here, see you next week.",
    ],
    "Greetings and intros": [
        "Welcome back to the channel everyone.",
        "Hey guys, welcome back to another video.",
        "Hello and welcome to my channel.",
        "What's up everybody, it's great to have you here.",
        "Welcome to today's video, let's get started.",
        "Hi everyone and welcome back.",
        "Good morning everyone and welcome to the show.",
        "Alright guys, welcome back to the channel.",
        "Before we begin, let me quickly say hello.",
        "Hello everybody, thanks for tuning in again.",
    ],
    "Sponsor reads": [
        "This video is sponsored by our friends at the store.",
        "A big thank you to our sponsor for supporting this channel.",
        "Use the promo code in the description to get a discount.",
        "Today's video is brought to you by a company I really trust.",
        "Check out our sponsor using the link below.",
        "Visit the sponsor's website and use my code for twenty percent off.",
        "This episode is supported by our partners.",
        "Sign up through the link in the description to support the show.",
        "Get your first month free with the code below.",
        "Special thanks to our sponsors who make this possible.",
    ],
    "Social media and links": [
        "Follow me on Instagram and Twitter for updates.",
        "Join our Discord community, the link is in the description.",
        "Check out my Patreon if you'd like to support the channel.",
        "Leave a comment below and tell me what you think.",
        "Share this video with your friends and family.",
        "Let me know in the comments what you'd like to see next.",
        "You can find all the links in the description below.",
        "Follow us on social media to stay in touch.",
        "Tell me your thoughts in the comment section.",
        "Don't forget to share this with someone who'd enjoy it.",
    ],
    "Empty filler talk": [
        "Okay, so, yeah, anyway.",
        "Alright, so let's see here.",
        "Right, okay, so, yeah, let's move on.",
        "Yeah, so, I mean, you know, whatever.",
        "Okay, okay, okay, so yeah.",
        "Uh, let me think about that for a second.",
        "So, yeah, that's pretty much it, right.",
        "Hmm, okay, well, yeah, so.",
        "Well, you know, like, it is what it is.",
        "Okay, so, um, where was I, right.",
    ],
}

# Real content that uses the same words in an ordinary way. Without these a model would just learn the
# words "subscribe", "watch", "thanks", "welcome"... instead of what makes a sentence redundant.
TRICKY_CONTENT = [
    "Watch how the planets move around the Sun in this simulation.",
    "The video shows a computer model of two galaxies colliding.",
    "Subscribers to the telescope's data feed receive new images every night.",
    "Thanks to gravity, the gas collapses into a star.",
    "The channel between the two planets is filled with dust and ice.",
    "Welcome to the edge of the solar system, where sunlight is a thousand times dimmer.",
    "Link the two observations together and the pattern becomes clear.",
    "Sponsored by the government, the mission launched in nineteen seventy seven.",
    "Follow the orbit of the comet and you will see it return to the same place.",
    "Join the two data sets and the signal becomes much easier to see.",
    "See how the temperature drops as we move away from the center of the star.",
    "Next time the comet returns will be in seventy six years.",
    "Hit by an asteroid, the planet's surface was completely reshaped.",
    "A notification of the discovery reached observatories around the world within hours.",
    "Share of the total mass held by the Sun is about ninety nine percent.",
    "The code that controls the spacecraft was written decades ago.",
    "Comment from the astronomers was that the signal looked far too regular.",
    "Like a stone in a pond, the explosion sent waves across the gas.",
    "The end of the star's life comes quickly once the fuel runs out.",
    "Thank you, Newton, for the equations that describe this motion.",
    "Good morning light reaches the planet's eastern edge about eight minutes after it leaves the Sun.",
    "Hello from a distance of twelve billion miles, the probe sent back one last picture.",
    "Today the telescope can see galaxies that formed shortly after the beginning of time.",
    "We will see why the Sun is so much hotter in its core than on its surface.",
]


def latest_per_video(docs: list[dict]) -> list[dict]:
    """A video may be transcribed by several ASR models - keep the newest transcript of each."""
    best: dict[str, dict] = {}
    for d in docs:
        cur = best.get(d["source_id"])
        if cur is None or d.get("created_at") and d["created_at"] > cur.get("created_at", d["created_at"]):
            best[d["source_id"]] = d
    return list(best.values())


def real_sentences(docs: list[dict]) -> list[str]:
    """Clear, complete sentences from the stored transcripts (confident speech, no obvious boilerplate)."""
    seen, out = set(), []
    for doc in latest_per_video(docs):
        for seg in doc.get("segments", []):
            conf = seg.get("confidence")
            if conf is not None and conf < LOW_CONFIDENCE:
                continue
            for s in rules.SENTENCE_SPLIT.split(seg["text"].strip()):
                s = s.strip()
                if len(s.split()) >= MIN_CONTENT_WORDS and s.lower() not in seen and not rules.is_boilerplate(s):
                    seen.add(s.lower())
                    out.append(s)
    return out


def base_sentences(real: list[str]) -> list[str]:
    """Real sentences that need NO cleaning, so mistakes can be added to them on purpose and the right answer is known."""
    return [s for s in real if MIN_CONTENT_WORDS + 1 <= len(s.split()) <= MAX_BASE_WORDS and rules.same_words(rules.clean_words(s), s)
            and len(words_of(s)) >= MIN_CONTENT_WORDS + 1]
