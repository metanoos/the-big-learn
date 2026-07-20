#!/usr/bin/env python3
"""
Manual re-alignment of the remaining lunyu + mengzi translation misalignments
that the automated fixer couldn't safely handle.

Each fix is derived by reading the combined English passage for a region,
identifying where Legge's sentence boundaries correspond to the Chinese unit
boundaries, and re-splitting. Every fix is keyed to exact (book, chapter, unit)
and validated against the Chinese source semantics.

Only `canonical_translations[0].text` is rewritten; all other structure is
preserved by parse + reserialize.
"""
import json, glob, os, sys

# Each entry: (book, chapter_file, [(unit_order, new_text), ...])
# The new_text is the precise English segment for that unit.
FIXES = [

# ===== LUNYU =====

# --- lunyu 2.5: u11-u13 (Meng Yi / Fan Chi on filial piety) ---
# Combined EN maps cleanly. u11 = Meng Yi question + "无违" reply + Fan Chi driving narrative.
# u12 = Fan Chi asks "what did you mean", u13 = Master's reply about serving/burying parents.
('lunyu', 'chapter-002.json', [
    (11, 'Meng Yi asked what filial piety was. The Master said, "It is not being disobedient." Soon after, as Fan Chi was driving him, the Master told him, saying, "Meng-sun asked me what filial piety was, and I answered him, - \'not being disobedient.\'"'),
    (12, 'Fan Chi said, "What did you mean?"'),
    (13, 'The Master replied, "That parents, when alive, be served according to propriety; that, when dead, they should be buried according to propriety; and that they should be sacrificed to according to propriety."'),
]),

# --- lunyu 7.31: u41-u43 (duke Zhao / propriety / partisan) ---
# u41 = minister asks + Confucius says "知礼". u42 = Confucius retires, minister's speech.
# u43 = Wu Ma Qi reports, Confucius's reply.
('lunyu', 'chapter-007.json', [
    (41, 'The minister of crime of Chen asked whether the duke Zhao knew propriety, and Confucius said, "He knew propriety."'),
    (42, 'Confucius having retired, the minister bowed to Wu Ma Qi to come forward, and said, "I have heard that the superior man is not a partisan. May the superior man be a partisan also? The prince married a daughter of the house of Wu, of the same surname with himself, and called her, \'The elder Zi of Wu.\' If the prince knew propriety, who does not know it?"'),
    (43, 'Wu Ma Qi reported these remarks, and the Master said, "I am fortunate! If I have any errors, people are sure to know them."'),
]),

# --- lunyu 11.24: u49-u51 (Zi Lu / injuring son / glib-tongued) ---
('lunyu', 'chapter-011.json', [
    (49, 'The Master said, "You are injuring a man\'s son."'),
    (50, 'Zi Lu said, "There are (there) common people and officers; there are the altars of the spirits of the land and grain. Why must one read books before he can be considered to have learned?"'),
    (51, 'The Master said, "It is on this account that I hate your glib-tongued people."'),
]),

# --- lunyu 12.8: u17-u19 (Ji Zi Cheng on substance vs ornament) ---
# u17 = Ji Zi Cheng's question, u18 = Zi Gong's reply (Alas! ... 驷不及舌), u19 = continuation.
('lunyu', 'chapter-012.json', [
    (17, 'Ji Zi Cheng said, "In a superior man it is only the substantial qualities which are wanted; why should we seek for ornamental accomplishments?"'),
    (18, 'Zi Gong said, "Alas! Your words, sir, show you to be a superior man, but four horses cannot overtake the tongue.'),
    (19, 'Ornament is as substance; substance is as ornament. The hide of a tiger or a leopard stripped of its hair, is like the hide of a dog or a goat stripped of its hair."'),
]),

# --- lunyu 12.20: u39-u44 (Zi Zhang on 达 distinction vs 闻 reputation) ---
# Legge's translation omits the Master's clarifying question (u40) and the 是闻也非达也
# interjection (u42), flowing from Zi Zhang's question straight into the definition.
# We re-segment so u40 gets the question (reconstructed from context), u41 gets Zi
# Zhang's reply, and u42-u44 get the Master's response distributed by clause.
('lunyu', 'chapter-012.json', [
    (40, 'The Master said, "What do you mean by that which you call distinction?"'),
    (41, 'Zi Zhang replied, "It is to be distinguished in the country; it is to be distinguished in one\'s clan."'),
    (42, 'The Master said, "That is reputation; it is not distinction.'),
    (43, 'Now the man of distinction is solid and straightforward, and loves righteousness. He examines people\'s words, and looks at their countenances. He is anxious to humble himself to others. Such a man will be distinguished in the country; he will be distinguished in his clan.'),
    (44, 'As to the man of notoriety, he assumes the appearance of virtue, but his actions are opposed to it, and he rests in this character without any doubts about himself. Such a man will be heard of in the country; he will be heard of in the clan."'),
]),

# --- lunyu 13.3: u6-u11 (rectification of names — full chain) ---
# u6 = 必也正名乎. u7 = Zi Lu 有是哉子之迂也. u8 = 野哉由也...盖阙如也.
# u9 = 名不正则言不顺...事不成. u10 = 事不成则礼乐不兴...民无所措手足.
# u11 = 故君子名之必可言也...无所苟而已矣.
('lunyu', 'chapter-013.json', [
    (6, 'The Master replied, "What is necessary is to rectify names."'),
    (7, '"So! indeed!" said Zi Lu. "You are wide of the mark! Why must there be such rectification?"'),
    (8, 'The Master said, "How uncultivated you are, You! A superior man, in regard to what he does not know, shows a cautious reserve.'),
    (9, 'If names be not correct, language is not in accordance with the truth of things. If language be not in accordance with the truth of things, affairs cannot be carried on to success.'),
    (10, 'When affairs cannot be carried on to success, proprieties and music will not flourish. When proprieties and music do not flourish, punishments will not be properly awarded. When punishments are not properly awarded, the people do not know how to move hand or foot.'),
    (11, 'Therefore a superior man considers it necessary that the names he uses may be spoken appropriately, and also that what he speaks may be carried out appropriately. What the superior man requires is just that in his words there may be nothing incorrect."'),
]),

# --- lunyu 13.9: u20-u23 (population / enrich / teach) ---
# u20 = 庶矣哉, u21 = 冉有 asks 既庶矣 + 富之, u22 = asks 既富矣 + 教之, u23 = 苟有用我者.
('lunyu', 'chapter-013.json', [
    (20, 'The Master observed, "How numerous are the people!"'),
    (21, 'You said, "Since they are thus numerous, what more shall be done for them?" "Enrich them," was the reply.'),
    (22, '"And when they have been enriched, what more shall be done?" The Master said, "Teach them."'),
    (23, 'The Master said, "If there were (any of the princes) who would employ me, in the course of twelve months, I should have done something considerable. In three years, the government would be perfected."'),
]),

# --- lunyu 14.21: u34-u37 (Chen Heng slain his sovereign) ---
# u34 = duke says 告夫三子, u35 = Confucius: 以吾从大夫之后..., u36 = 之三子告不可 + repeated statement, u37 = Zi Lu问事君.
('lunyu', 'chapter-014.json', [
    (34, 'The duke said, "Inform the chiefs of the three families of it."'),
    (35, 'Confucius retired, and said, "Following in the rear of the great officers, I did not dare not to represent such a matter, and my prince says, \'Inform the chiefs of the three families of it.\'"'),
    (36, 'He went to the chiefs, and informed them, but they would not act. Confucius then said, "Following in the rear of the great officers, I did not dare not to represent such a matter."'),
    (37, 'Zi Lu asked how a ruler should be served. The Master said, "Do not impose on him, and, moreover, withstand him to his face."'),
]),

# --- lunyu 14.35: u56-u57 (no one knows me / Zi Gong / Heaven) ---
# u56 = 莫我知也夫, u57 = Zi Gong asks + Master's 不怨天不尤人 reply.
('lunyu', 'chapter-014.json', [
    (56, 'The Master said, "Alas! there is no one that knows me."'),
    (57, 'Zi Gong said, "What do you mean by thus saying - that no one knows you?" The Master replied, "I do not murmur against Heaven. I do not grumble against men. My studies lie low, and my penetration rises high. But there is Heaven - that knows me!"'),
]),

# --- lunyu 16.1: u8-u12 NOT FIXED ---
# The Chinese u8 (今夫颛臾固而近于费) and u9 (孔子曰求君子疾夫) have NO corresponding
# English in Legge's translation — he appears to have condensed this section.
# Cannot re-align without inventing text; left as-is.

# --- lunyu 11.25: u54-u57 (Zi Lu / Ran You / Gongxi Hua wishes) — verbatim re-split ---
('lunyu', 'chapter-011.json', [
    (54, 'From day to day you are saying, \'We are not known.\' If some ruler were to know you, what would you like to do?"'),
    (55, 'Zi Lu hastily and lightly replied, "Suppose the case of a state of ten thousand chariots; let it be straitened between other large states; let it be suffering from invading armies; and to this let there be added a famine in corn and in all vegetables - if I were intrusted with the government of it, in three years\' time I could make the people to be bold, and to recognize the rules of righteous conduct." The Master smiled at him.'),
]),

# --- lunyu 4.5-4.7: u5-u7 (riches/honor · abandon virtue · single meal) ---
# Legge's translation for this passage is split one unit behind the Chinese:
# u5's EN holds only the opening fragment, u6 holds u5's continuation, and u7
# holds u6's content followed by its own. The automated aligner missed this
# because every segment ends in terminal punctuation (so the mid-thought
# trigger never fired). Re-split by Legge's sentence boundaries mapped to the
# Chinese units: u5 = 富与贵…不处也 / 贫与贱…不去也, u6 = 君子去仁恶乎成名,
# u7 = 终食之间违仁…颠沛必于是 (also owns the closing quote — 」lands here).
('lunyu', 'chapter-004.json', [
    (5, 'The Master said, "Riches and honors are what men desire. If it cannot be obtained in the proper way, they should not be held. Poverty and meanness are what men dislike. If it cannot be avoided in the proper way, they should not be avoided.'),
    (6, 'If a superior man abandon virtue, how can he fulfill the requirements of that name?'),
    (7, 'The superior man does not, even for the space of a single meal, act contrary to virtue. In moments of haste, he cleaves to it. In seasons of danger, he cleaves to it."'),
]),

# --- lunyu 4.6-4.8 (Legge numbering): u8-u10 (loving virtue · strength · possibly) ---
# Same forward-leak pattern as u5-u7 above: u8 truncated to its opening, u9
# holds u8's continuation, u10 holds u8's tail + its own. Re-split by Legge's
# sentence boundaries: u8 = 未见好仁者…加乎其身 (owns the opening quote), u9 =
# 有能一日用其力于仁矣乎 / 未见力不足者, u10 = 盖有之矣我未之见也 (owns the
# closing quote — 」lands here).
('lunyu', 'chapter-004.json', [
    (8, 'The Master said, "I have not seen a person who loved virtue, or one who hated what was not virtuous. He who loved virtue, would esteem nothing above it. He who hated what is not virtuous, would practice virtue in such a way that he would not allow anything that is not virtuous to approach his person.'),
    (9, 'Is any one able for one day to apply his strength to virtue? I have not seen the case in which his strength would be insufficient.'),
    (10, 'Should there possibly be any such case, I have not seen it."'),
]),

# --- lunyu 4.26: u31 (Zi You on remonstrance) ---
# Scraper boilerplate ("Source: Chinese Text Project ... Dictionary cache status:
# not loaded Glossary and Other Vocabulary") was appended to Legge's translation
# during ingest. Strip it; the Legge sentence itself is the unit's full content.
('lunyu', 'chapter-004.json', [
    (31, 'Zi You said, "In serving a prince, frequent remonstrances lead to disgrace. Between friends, frequent reproofs make the friendship distant."'),
]),

# ===== LUNYU CHAPTER 5 (公冶长) =====
# Same forward-leak class of error as chapter 4, plus the u39 scraper boiler-
# plate. The automated aligner missed these because the truncated units still
# end in terminal punctuation (period, or close-quote that Legge punctuates
# with a period), so the mid-thought trigger never fired.

# --- lunyu 5.5: u5-u6 (Yong virtuous but not glib) ---
# u5 = 或曰雍也仁而不佞 (someone's remark), u6 = 子曰焉用佞... (Master's reply).
# u5's EN was carrying the first sentence of the Master's reply; pull it into u6.
('lunyu', 'chapter-005.json', [
    (5, 'Some one said, "Yong is truly virtuous, but he is not ready with his tongue."'),
    (6, 'The Master said, "What is the good of being ready with the tongue? They who encounter men with smartness of speech for the most part procure themselves hatred. I know not whether he be truly virtuous, but why should he show readiness of the tongue?"'),
]),

# --- lunyu 5.8: u9-u12 (Meng Wu asks about Zi Lu / Qiu / Chi) ---
# Four-way forward-leak: u9 (问子路仁乎 + 不知也) truncated to its opening clause,
# u10 (又问 + 治其赋) holding only u9's continuation, u11 (求也何如 + 为之宰)
# collapsed to "The Master said,", and u12 (赤也何如 + 与宾客言) carrying all
# four units' English. Re-split by Legge's sentence boundaries mapped to the
# three disciple question/answer pairs.
('lunyu', 'chapter-005.json', [
    (9, 'Meng Wu asked about Zi Lu, whether he was perfectly virtuous. The Master said, "I do not know."'),
    (10, 'He asked again, when the Master replied, "You, in a kingdom of a thousand chariots, might be employed to manage the military levies, but I do not know whether he be perfectly virtuous."'),
    (11, '"And what do you say of Qiu?" The Master replied, "Qiu, in a city of a thousand families, or a clan of a hundred chariots, might be employed as governor, but I do not know whether he is perfectly virtuous."'),
    (12, '"What do you say of Chi?" The Master replied, "Chi, with his sash girt and standing in a court, might be employed to converse with the visitors and guests, but I do not know whether he is perfectly virtuous."'),
]),

# --- lunyu 5.9: u13-u15 (Zi Gong compared to Hui) ---
# Each unit's EN was carrying the opening of the next. u13 = Master's question,
# u14 = Zi Gong's reply, u15 = Master's verdict.
('lunyu', 'chapter-005.json', [
    (13, 'The Master said to Zi Gong, "Which do you consider superior, yourself or Hui?"'),
    (14, 'Zi Gong replied, "How dare I compare myself with Hui? Hui hears one point and knows all about a subject; I hear one point, and know a second."'),
    (15, 'The Master said, "You are not equal to him. I grant you, you are not equal to him."'),
]),

# --- lunyu 5.10: u16-u17 (Zai Yu sleeping by day) ---
# u16 truncated mid-sentence (于予与何诛 split across the boundary), u17 holds
# the tail of u16 plus its own. Re-split so u16 owns the rotten-wood rebuke
# and u17 owns the hear-their-words reflection.
('lunyu', 'chapter-005.json', [
    (16, 'Zai Yu being asleep during the daytime, the Master said, "Rotten wood cannot be carved; a wall of dirty earth will not receive the trowel. This Yu! - what is the use of my reproving him?"'),
    (17, 'The Master said, "At first, my way with men was to hear their words, and give them credit for their conduct. Now my way is to hear their words, and look at their conduct. It is from Yu that I have learned to make this change."'),
]),

# --- lunyu 5.19: u26-u27 (Zi Wen loyal / Chen Wen pure) ---
# u26 truncated after the first clause of Zi Wen's story; u27 holds the rest of
# u26 plus its own (Chen Wen / officer Cui). Re-split so each unit owns its own
# disciple anecdote + the 仁矣乎 / 未知，焉得仁 exchange that closes it.
('lunyu', 'chapter-005.json', [
    (26, 'Zi Zhang asked, saying, "The minister Zi Wen thrice took office, and manifested no joy in his countenance. Thrice he retired from office, and manifested no displeasure. He made it a point to inform the new minister of the way in which he had conducted the government - what do you say of him?" The Master replied. "He was loyal." "Was he perfectly virtuous?" "I do not know. How can he be pronounced perfectly virtuous?"'),
    (27, 'Zi Zhang proceeded, "When the officer Cui killed the prince of Qi, Chen Wen, though he was the owner of forty horses, abandoned them and left the country. Coming to another state, he said, \'They are here like our great officer, Cui,\' and left it. He came to a second state, and again said \'They are here like our great officer, Cui,\' and left it also - what do you say of him?" The Master replied, "He was pure." "Was he perfectly virtuous?" "I do not know. How can he be pronounced perfectly virtuous?"'),
]),

# --- lunyu 5.28: u39 (hamlet of ten families) ---
# Scraper boilerplate ("Source: Chinese Text Project ... Dictionary cache status:
# not loaded Glossary and Other Vocabulary") appended to Legge's translation
# during ingest. Strip it.
('lunyu', 'chapter-005.json', [
    (39, 'The Master said, "In a hamlet of ten families, there may be found one honorable and sincere as I am, but not so fond of learning."'),
]),

# ===== MENGZI =====

# --- mengzi 4.B: u31-u33 (Mencius's mission to Teng / coffin) ---
# u31 = Mencius at Qi, mission to Teng, Wang Huan. u32 = Gong Sun Chou's question + Mencius's reply.
# u33 = Mencius buries mother in Lu, Chong Yu asks about coffin.
('mengzi', 'chapter-004.json', [
    (31, 'Mencius, occupying the position of a high dignitary in Qi, went on a mission of condolence to Teng. The king also sent Wang Huan, the governor of Gai, as assistant-commissioner. Wang Huan, morning and evening, waited upon Mencius, who, during all the way to Teng and back, never spoke to him about the business of their mission.'),
    (32, 'Gong Sun Chou said to Mencius, \'The position of a high dignitary of Qi is not a small one; the road from Qi to Teng is not short. How was it that during all the way there and back, you never spoke to Huan about the matters of your mission?\' Mencius replied, \'There were the proper officers who attended to them. What occasion had I to speak to him about them?\''),
    (33, 'Mencius went from Qi to Lu to bury his mother. On his return to Qi, he stopped at Ying, where Chong Yu begged to put a question to him, and said, \'Formerly, in ignorance of my incompetency, you employed me to superintend the making of the coffin. As you were then pressed by the urgency of the business, I did not venture to put any question to you. Now, however, I wish to take the liberty to submit the matter. The wood of the coffin, it appeared to me, was too good.\''),
]),

# --- mengzi 8.30: u70-u79 (Kuang Zhang unfilial / Zeng & Zisi / officer Chu) ---
# This region's combined English flows correctly but is mis-segmented. Re-split by clause.
('mengzi', 'chapter-008.json', [
    (70, 'The disciple Gong Du said, \'Throughout the whole kingdom everybody pronounces Kuang Zhang unfilial. But you, Master, keep company with him, and moreover treat him with politeness. I venture to ask why you do so.\''),
    (71, 'Mencius replied, \'There are five things which are pronounced in the common usage of the age to be unfilial. The first is laziness in the use of one\'s four limbs, without attending to the nourishment of his parents. The second is gambling and chess-playing, and being fond of wine, without attending to the nourishment of his parents. The third is being fond of goods and money, and selfishly attached to his wife and children, without attending to the nourishment of his parents. The fourth is following the desires of one\'s ears and eyes, so as to bring his parents to disgrace. The fifth is being fond of bravery, fighting and quarrelling so as to endanger his parents. Is Zhang guilty of any one of these things?'),
    (72, 'Now between Zhang and his father there arose disagreement, he, the son, reproving his father, to urge him to what was good.'),
    (73, 'To urge one another to what is good by reproofs is the way of friends. But such urging between father and son is the greatest injury to the kindness, which should prevail between them.'),
    (74, 'Moreover, did not Zhang wish to have in his family the relationships of husband and wife, child and mother? But because he had offended his father, and was not permitted to approach him, he sent away his wife, and drove forth his son, and all his life receives no cherishing attention from them. He settled it in his mind that if he did not act in this way, his would be one of the greatest of crimes. Such and nothing more is the case of Zhang.\''),
    (75, 'When the philosopher Zeng dwelt in Wu Cheng, there came a band from Yue to plunder it. Someone said to him, \'The plunderers are coming - why not leave this?\' Zeng on this left the city, saying to the man in charge of the house, \'Do not lodge any persons in my house, lest they break and injure the plants and trees.\' When the plunderers withdrew, he sent word to him, saying, \'Repair the walls of my house. I am about to return.\' When the plunderers retired, the philosopher Zeng returned accordingly. His disciples said, \'Since our master was treated with so much sincerity and respect, for him to be the first to go away on the arrival of the plunderers, so as to be observed by the people, and then to return on their retiring, appears to us to be improper.\''),
    (76, 'Shen You Xing said, \'You do not understand this matter. Formerly, when Shen You was exposed to the outbreak of the grass-carriers, there were seventy disciples in our master\'s following, and none of them took part in the matter.\''),
    (77, 'When Zi Si was living in Wei, there came a band from Qi to plunder. Some one said to him, \'The plunderers are coming - why not leave this?\' Zi Si said, \'If I go away, whom will the prince have to guard the State with?\''),
    (78, 'Mencius said, \'The philosophers Zeng and Zi Si agreed in the principle of their conduct. Zeng was a teacher - in the place of a father or elder brother. Zi Si was a minister - in a meaner place. If the philosophers Zeng and Zi Si had exchanged places the one would have done what the other did.\''),
    (79, 'The officer Chu said to Mencius, \'Master, the king sent persons to spy out whether you were really different from other men.\' Mencius said, \'How should I be different from other men?'),
]),

# --- mengzi 9.A: u1-u4 (Wan Zhang asks about Shun weeping) ---
# Re-split by clause boundaries matching Chinese units.
('mengzi', 'chapter-009.json', [
    (1, 'Wan Zhang asked Mencius, saying, \'When Shun went into the fields, he cried out and wept to the pitying heavens. To what did he cry out and weep?\' Mencius answered, \'Because of his resentment and longing for his parents.\''),
    (2, 'Wan Zhang said, \'When his parents love him, a son rejoices and does not forget them; when they hate him, though he labours for them, he does not murmur. Did Shun then murmur?\' Mencius said, \'Chang Xi asked Gong Ming Gao, saying, "As to Shun\'s going into the fields, I have received your instructions, but I do not know about his weeping and crying out to the pitying heavens and to his parents." Gong Ming Gao answered him, "You do not understand that matter."'),
    (3, 'Now, Gong Ming Gao supposed that the heart of the filial son could not be so free of sorrow. Shun would say, "I exert my strength to cultivate the fields, but I am thereby only discharging my office as a son. What can there be in me that my parents do not love me?"'),
    (4, 'The Di caused his own children, nine sons and two daughters, the various officers, oxen and sheep, storehouses and granaries, all to be prepared, to serve Shun amid the channelled fields. Of the scholars of the kingdom there were multitudes who flocked to him. The Di was about to transfer the kingdom to him, but because he was not in accord with his parents, he was like a man in distress who has nowhere to turn.'),
]),

# --- mengzi 9.A: u52-u55 (Bai Li Xi sold himself) ---
# u53 = Wan Zhang's question about Bai Li Xi, Mencius: 否不然好事者为之也.
# u54 = 百里奚虞人也... 百里奚不谏. u55 = 知虞公之不可谏而去...
('mengzi', 'chapter-009.json', [
    (53, 'Wan Zhang asked, \'Some say that Bai Li Xi sold himself to a cattle-breeder of Qin, for the skins of five rams, and fed his oxen, in order to seek the favour of duke Mu of Qin. Is this the case?\' Mencius said, \'No; it is not so. The story was invented by an officious maker of stories.'),
    (54, 'Bai Li Xi was a man of Yu. The people of Jin, by means of the gem of Chui Ji, and the horses of Qu Chan, begged a passage through Yu to attack Guo. Gong Zhi Qi remonstrated against giving them the passage, but Bai Li Xi did not remonstrate.'),
    (55, 'Knowing that the duke of Yu could not be remonstrated with, he went away and entered Qin, being then already seventy years. If he had not known that it would be a disgrace to seek the favour of duke Mu of Qin by feeding his oxen, could he be called wise? Not to remonstrate where he could not remonstrate, could he be called not wise? Knowing that the duke of Yu would be ruined, and therefore leaving him beforehand, can he be called not wise? When raised to office in Qin, he knew that duke Mu was one with whom he might accomplish something, and left him accordingly - can he be called not wise?'),
]),

# --- mengzi 10.B: u16-u19 (friendship / Meng Xian) ---
('mengzi', 'chapter-010.json', [
    (17, 'Wan Zhang asked, \'I venture to ask about friendship.\' Mencius replied, \'Friendship should be maintained without any presumption on the ground of one\'s superior age, or station, or the circumstances of his relatives. Friendship with a man is friendship with his virtue, and does not admit of assumptions of superiority.'),
    (18, 'There was Meng Xian, chief of a family of a hundred chariots.'),
    (19, 'He had five friends - Yue Zheng Qiu, Mu Zhong, and three others whose names I have forgotten. Meng Xian maintained his friendship with these five men without any presumption from his position; and these five men also, if they had had such thoughts of his position, would not have maintained their friendship with him.'),
]),

# --- mengzi 10.B: u25-u28 (robber's gift / Announcement to Kang) ---
('mengzi', 'chapter-010.json', [
    (26, 'Wan Zhang said, \'Suppose the case of a man who stops another on the highway outside the gates of a city. He offers his gift on a ground of reason, and does so in a manner according to propriety - would the reception of it so acquired by robbery be proper?\' Mencius replied, \'It would not be proper. In "The Announcement to Kang" it is said, "When men kill others, and roll over their bodies to take their property, being reckless and fearless of death, among all the people there are none but detest them" - thus, such characters are to be put to death, without waiting to give them warning. Yin received this rule from Xia and Zhou received it from Yin. It cannot be questioned, and to the present day is clearly acknowledged. How can the gift of a robber be received?\''),
    (27, 'Zhang said, \'The princes of the present day take from their people just as a robber despoils his victim. Yet if they put a good face of propriety on their gifts, then the superior man receives them. I venture to ask how you explain this.\' Mencius answered, \'Do you think that, if there should arise a truly royal sovereign, he would collect the princes of the present day, and put them all to death? Or would he admonish them, and then, on their not changing their ways, put them to death? Indeed, to call every one who takes what does not properly belong to him a robber, is pushing a point of resemblance to the utmost, and insisting on the most refined idea of righteousness.'),
    (28, 'When Confucius was in office in Lu, the people struggled together for the game taken in hunting, and he also did the same. If that struggling for the captured game was proper, how much more may the gifts of the princes be received!\''),
]),

# --- mengzi 10.B: u30-u34 (Confucius taking office) — verbatim from combined ---
# The combined has a duplicate "Confucius took office..." block; we map the first
# occurrence to u30, and u31 gets the "Mencius said, Office is not sought..." which
# sits after the duplicate. u32/u33 are not separately present (Legge condensed).
('mengzi', 'chapter-010.json', [
    (30, 'Confucius took office when he saw that the practice of his doctrines was likely; he took office when his reception was proper; he took office when he was supported by the State. In the case of his relation to Qi Huan, he took office, seeing that the practice of his doctrines was likely. With the duke Ling of Wei he took office, because his reception was proper. With the duke Xiao of Wei he took office, because he was maintained by the State.\''),
    (31, 'Mencius said, \'Office is not sought on account of poverty, yet there are times when one seeks office on that account. Marriage is not entered into for the sake of being attended to by the wife, yet there are times when one marries on that account.'),
    (32, 'He who takes office on account of poverty should decline a high station and accept a low one; should decline riches and accept poverty.'),
    (33, 'In declining a high station and accepting a low one, in declining riches and accepting poverty, what office would be proper? That of a gate-keeper or a watchman beating the rattle.'),
]),

# --- mengzi 10.B: u42-u45 (not seeing princes / Zi Si) ---
('mengzi', 'chapter-010.json', [
    (42, 'Wan Zhang said, \'I venture to ask what principle of righteousness is involved in a scholar\'s not going to see the princes?\' Mencius replied, \'A scholar residing in the city is called "a minister of the market-place and well," and one residing in the country is called "a minister of the grass and plants." In both cases he is a common man, and it is the rule of propriety that common men, who have not presented the introductory present and become ministers, should not presume to have interviews with the prince.\''),
    (43, 'Wan Zhang said, \'If a common man is called to perform any service, he goes and performs it; how is it that a scholar, when the prince, wishing to see him, calls him to his presence, refuses to go?\' Mencius replied, \'It is right to go and perform the service; it would not be right to go and see the prince.'),
    (44, 'And,\' added Mencius, \'on what account is it that the prince wishes to see the scholar?\' \'Because of his extensive information, or because of his talents and virtue,\' was the reply. \'If because of his extensive information,\' said Mencius, \'such a person is a teacher, and the sovereign would not call him - how much less may any of the princes do so? If because of his talents and virtue, then I have not heard of any one wishing to see a person with those qualities, and calling him to his presence.'),
    (45, 'Duke Mu hastened to see Zi Si, and said, "Anciently, how was it that a state of a thousand chariots made friends with a scholar?" Zi Si was displeased, and said, "The ancients have said, \'Was it to serve him?\' - how could they say merely, \'Was it to make a friend of him?\'" Zi Si\'s displeasure might be interpreted thus: "In point of rank, you are the ruler; I am the subject. How should I dare to make a friend of you?"'),
]),

# --- mengzi 10.B: u50-u54 (friendship across ranks / high ministers) ---
('mengzi', 'chapter-010.json', [
    (51, 'Wan Zhang said, \'When Confucius received the prince\'s message calling him, he went without waiting for his carriage. Doing so, did Confucius do wrong?\' Mencius replied, \'Confucius was in office, and had to observe its appropriate duties. And moreover, he was summoned on the business of his office.\''),
    (52, 'Mencius said to Wan Zhang, \'The scholar whose virtue is most distinguished in a village shall make friends of all the virtuous scholars in the village. The scholar whose virtue is most distinguished throughout a State shall make friends of all the virtuous scholars of that State. The scholar whose virtue is most distinguished throughout the kingdom shall make friends of all the virtuous scholars of the kingdom.'),
    (53, 'When a scholar feels that his friendship with all the virtuous scholars of the kingdom is not sufficient to satisfy him, he proceeds to ascend to consider the men of antiquity. He repeats their poems, and reads their books, and as he does not know what they were as men, to ascertain this, he considers their history. This is to ascend and make friends of the men of antiquity.\''),
    (54, 'The king Xuan of Qi asked about the office of high ministers. Mencius said, \'Which high ministers is your Majesty asking about?\' \'Are there differences among them?\' inquired the king. \'There are\' was the reply. \'There are the high ministers who are noble and relatives of the prince, and there are those who are of a different surname.\' The king said, \'I beg to ask about the high ministers who are noble and relatives of the prince.\' Mencius answered, \'If the prince have great faults, they ought to remonstrate with him, and if he do not listen to them after they have done so again and again, they ought to dethrone him.\''),
]),

]


def apply_fixes(apply=False):
    # Group fixes by (book, chapter)
    by_chapter = {}
    for book, chf, unit_fixes in FIXES:
        by_chapter.setdefault((book, chf), []).extend(unit_fixes)

    total_changed = 0
    skipped_reconstructed = 0
    for (book, chf), unit_fixes in by_chapter.items():
        path = f'content/books/{book}/chapters/{chf}'
        with open(path, encoding='utf-8') as f:
            ch = json.load(f)
        units = {u['order']: u for u in ch['chapter']['reading_units']}
        # Build combined english for the region to verify verbatim
        orders = [o for o, _ in unit_fixes]
        region = [u for o, u in sorted(units.items()) if min(orders) <= o <= max(orders)]
        combined = ' '.join(u['canonical_translations'][0]['text'] for u in region).lower()

        changed = False
        for order, new_text in unit_fixes:
            if order not in units:
                print(f"  !! unit u{order} not found in {path}", file=sys.stderr)
                continue
            # SAFETY: only apply if new_text is verbatim from the combined Legge text
            if new_text.lower() not in combined:
                skipped_reconstructed += 1
                continue
            u = units[order]
            old = u['canonical_translations'][0]['text']
            if old != new_text:
                print(f"[{'APPLY' if apply else 'DRY'}] {book}/{chf} u{order}")
                print(f"   CN:  {u['text'][:60]}")
                print(f"   OLD: {old[:90]}")
                print(f"   NEW: {new_text[:90]}")
                u['canonical_translations'][0]['text'] = new_text
                changed = True
                total_changed += 1
        if changed and apply:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(ch, f, ensure_ascii=False, indent=2)
                f.write('\n')
            with open(path, encoding='utf-8') as f:
                json.load(f)  # validate
            print(f"   -> written and validated")
        print()

    print(f"Total units changed: {total_changed}")
    print(f"Skipped (reconstructed/non-verbatim): {skipped_reconstructed}")


if __name__ == '__main__':
    apply_fixes(apply='--apply' in sys.argv)
