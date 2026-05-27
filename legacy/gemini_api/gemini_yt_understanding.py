from google import genai
from google.genai import types
prompt = """
Analyze this YouTube video for editing insights.

Return JSON with:
- summary
- key_topics
- important_moments: [{timestamp, description}]
- best_short_form_clips: [{start, end, hook, reason}]
- overall_engagement_assessment
"""

#test

client = genai.Client()
response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents=types.Content(
        parts=[
            types.Part(
                file_data=types.FileData(file_uri='https://www.youtube.com/watch?v=jIS2eB-rGv0&t=218s')
            ),
            types.Part(text=prompt)
        ]
    )
)
print(response.text)
#explain output in json format for this video: https://www.youtube.com/watch?v=jIS2eB-rGv0&t=218s
# json
# {
#   "summary": "This video presents a deep dive into a hypothetical 'World War III' scenario involving the United States, Israel, and Iran. The speaker uses game theory and geographic analysis to evaluate the strategies, vulnerabilities, and potential outcomes of the conflict, specifically focusing on the economic collapse of the 'American Empire' via the petrodollar and resource-based warfare involving oil and water.",
#   "key_topics": [
#     "Geopolitics",
#     "Game Theory",
#     "Middle Eastern Conflict",
#     "Asymmetric Warfare",
#     "Petrodollar and Global Economy",
#     "Resource Scarcity (Water/Oil)"
#   ],
#   "important_moments": [
#     {
#       "timestamp": "00:00",
#       "description": "Introduction to the 'End of the World' and the start of a hypothetical WWIII involving attacks on Iran."
#     },
#     {
#       "timestamp": "01:06",
#       "description": "Analysis of the decapitation strike against the Ayatollah and the Iranian perception of martyrdom versus the Western perception of victory."
#     },
#     {
#       "timestamp": "05:54",
#       "description": "Impact of Iranian attacks on Dubai and the GCC, arguing that the city's reputation as a safe haven is permanently destroyed."
#     },
#     {
#       "timestamp": "11:12",
#       "description": "Explaining the strategic importance of the Strait of Hormuz for global oil flow and GCC food imports."
#     },
#     {
#       "timestamp": "14:42",
#       "description": "Analysis of the geographical mismatch: Iran's mountain fortress versus the exposed GCC desert terrain."
#     },
#     {
#       "timestamp": "18:30",
#       "description": "The Western strategy of fracturing Iran based on ethnic minorities and water scarcity."
#     },
#     {
#       "timestamp": "20:03",
#       "description": "Discussion of asymmetric warfare: using $50,000 Shahed drones to overwhelm million-dollar THAAD missile systems."
#     },
#     {
#       "timestamp": "25:35",
#       "description": "The Iranian counter-strategy: inciting global Jihad to unify the Muslim world against Western influence."
#     },
#     {
#       "timestamp": "26:00",
#       "description": "The economic 'kill shot': how a GCC collapse triggers a US stock market crash due to trillions in invested assets."
#     }
#   ],
#   "best_short_form_clips": [
#     {
#       "start": "20:03",
#       "end": "21:00",
#       "hook": "Why the US military is failing the 21st-century test.",
#       "reason": "This segment clearly explains the math of asymmetric warfare (cheap drones vs. expensive missiles), which is a high-interest topic in modern military analysis."
#     },
#     {
#       "start": "06:16",
#       "end": "07:10",
#       "hook": "Dubai as we know it is dead.",
#       "reason": "A bold, controversial prediction about a major global hub grabs immediate attention."
#     },
#     {
#       "start": "14:50",
#       "end": "15:45",
#       "hook": "The secret reason the US dollar is worth something.",
#       "reason": "Explaining the petrodollar and its connection to Middle Eastern stability is a classic educational hook that appeals to finance and political buffs."
#     }
#   ],
#   "overall_engagement_assessment": "The video is highly engaging due to its 'high-stakes' subject matter and the use of a large interactive screen for visual storytelling. The speaker maintains a calm, authoritative tone while delivering controversial and alarming analysis, which creates a 'forbidden knowledge' appeal. The data-driven approach with maps and economic charts provides significant informational value."
# }