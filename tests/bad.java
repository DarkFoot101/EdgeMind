class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:
        maxLength = 0
        left = 0
        lastSeen = {}

        for right in range(len(s)):
            c = s[right]
            if c in lastSeen and lastSeen[c] >= left:
                left = lastSeen[c] + 1
            lastSeen[c] = right
            maxLength = max(maxLength, right - left + 1)

        return maxLength