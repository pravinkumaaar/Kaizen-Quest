# Learning Curator Skill#

## Description#
Manages the weekly learning theme system: rotating themes, daily deep-dives, educational content curation, and learning progress tracking.#

## When to Use#
- Generating daily learning recommendations#
- Managing weekly theme rotation (every 7 days)#
- Creating daily deep-dive content#
- Tracking learning progress#

## Instructions#

### 1. Weekly Theme System#
**Rotation**: Every 7 days, auto-rotate to next theme.#
**Themes available**:#
1. **Macroeconomics**: Money, inflation, Fed policy, supply/demand#
2. **History Repeats**: Tulip mania, Dot-com, 2008, crypto winters#
3. **Artificial Intelligence**: LLMs, neural networks, AI alignment#
4. **Energy & Climate**: Renewables, nuclear, grid challenges#
5. **Human Longevity**: Aging biology, biohacking, biotech#

### 2. Daily Deep-Dives#
**Format**: Based on day of week (0=Monday, 6=Sunday)#
- Day 1: Foundation concepts#
- Day 2: Mechanisms/how it works#
- Day 3: Real-world applications#
- Day 4: Investment implications#
- Day 5: Risks and limitations#
- Day 6: Cross-domain connections#
- Day 7: Summary and wrap-up#

### 3. Generate Learning Content#
Structure:#
```markdown#
## 📚 This Week's Theme#
**{Theme Name}**#
Progress: Day X of 7#

## Today's Focus: {Subtopic}#
2-3 paragraphs explaining the concept clearly.#
- Why does this matter for an investor/learner?#
- How does it connect to AI, economics, or human behavior?#
- What's one practical takeaway they can apply this week?#

## Action Items#
1. [ ] Read/Watch: Suggest 1-2 specific resources (URLs if possible)#
2. [ ] Reflect: Write down 3 key takeaways#
3. [ ] Connect: How does this relate to your current investments/interests?#

## Portfolio Connection#
How does today's topic affect your holdings or investment thinking?#
```

### 4. Cross-Domain Insights#
Always connect to:#
- **AI**: How does this relate to AI development?#
- **Economics**: What are the investment implications?#
- **History**: What patterns from the past apply?#
- **Science**: How does this impact human behavior?#

## Output Format#

```markdown#
## 📚 Learning Recommendation#

**This Week's Theme:** The AI Revolution: How Large Language Models Work#
**Progress:** Day 3 of 7#

## Today's Deep Dive: Training & Scaling Laws#
Why does this matter? Larger models with more data generally perform better, but with diminishing returns. Understanding scaling helps predict which AI companies will dominate.#

Connection: Companies like Nvidia (NVDA) benefit from the compute arms race. Cloud providers (MSFT, GOOGL) need massive infrastructure.#

## Action Items#
1. [ ] Read: "Scaling Laws for Neural Language Models" (Kaplan et al., 2020)#
2. [ ] Reflect: Why does bigger = better (until it doesn't)?#
3. [ ] Connect: How does this affect your NVDA/AMD holdings?#

## Portfolio Connection#
Your tech holdings (NVDA, MSFT, GOOGL) directly benefit from AI scaling. Consider if allocation matches conviction.#
```

## Key Reminders#
- Use 📚 emoji for learning content#
- Always include 3 action items (read, reflect, connect)#
- Connect to portfolio holdings when relevant#
- Keep it substantive but concise (800-1000 words)#
- Rotate themes weekly (check 7-day interval)#
- Mark progress: ✅ completed, [ ] pending#
