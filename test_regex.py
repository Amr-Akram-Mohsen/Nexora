import re
text = 'Add Yahoo as a preferred source to see more of our stories on Google. Leigh-Anne Pinnock is expanding her family, and she used a studio video to make the announcement. People reported that the Little Mix singer, 34, is pregnant and expecting her third child with her husband, soccer player Andre Gray. The couple already shares twin daughters, who were born in August 2021. Pinnock Announced the News With a Studio Video Pinnock captioned the Instagram video, "As one chapter ends, another begins," and set the post to her song "Heaven."'

try:
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])', text)
    print("Success")
    print(sentences)
except Exception as e:
    print(f"Error: {e}")
