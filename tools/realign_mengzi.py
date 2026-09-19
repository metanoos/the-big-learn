#!/usr/bin/env python3
"""Realign mengzi chapters 2-14 canonical_translations to reading units.

Same model as realign_mengzi_ch1_apply.py: each chapter's English (corpus
edition of Legge) is a global fragment stream that is complete and in order,
but fragments were cut into the wrong reading units. This script:

  realign_mengzi.py workbench <chapter>   -> print ZH segments + EN fragments
  realign_mengzi.py apply <chapter>       -> apply ASSIGN/RESTORES/DUP tables

The ASSIGN/RESTORES/DUP tables below are per-chapter, hand-verified by
reading every unit's ZH against its assigned EN (same process as ch1).
"""
import json
import re
import sys

CONTENT = "/Users/peterwei/wokshop/the-big-learn/content/books/mengzi/chapters"

# ---------------------------------------------------------------------------
# Per-chapter assignment tables: unit order -> [start, end) into the global
# EN fragment stream. Fragments NOT covered by any unit are duplicated
# blocks to drop. RESTORES: unit -> (position, text) for sentences missing
# from the corpus stream (scrape truncation), sourced from the corpus's own
# cited public-domain Wikisource pages.
# ---------------------------------------------------------------------------
TABLES = {
    # 2: 梁惠王下
    2: {
        "assign": {
            1: (0, 4), 2: (4, 6), 3: (6, 9), 4: (9, 13), 5: (13, 14),
            6: (14, 22), 7: (22, 25), 8: (25, 32), 9: (32, 33), 10: (33, 35),
            11: (35, 42), 12: (42, 45), 13: (45, 49), 14: (49, 53),
            15: (53, 54), 16: (54, 56), 17: (56, 57), 18: (57, 60),
            19: (60, 66), 20: (66, 68), 21: (68, 70), 22: (70, 71),
            23: (71, 73), 24: (73, 75), 25: (75, 78), 26: (78, 78),
            27: (78, 78), 28: (78, 79), 29: (79, 80), 30: (80, 87),
            31: (87, 89), 32: (89, 91), 33: (91, 97), 34: (97, 98),
            35: (98, 107), 36: (107, 108), 37: (108, 113), 38: (113, 115),
            39: (115, 117), 40: (117, 119), 41: (119, 122), 42: (122, 123),
            43: (123, 125), 44: (125, 131), 45: (131, 135), 46: (135, 136),
            47: (136, 138), 48: (138, 139), 49: (139, 142), 50: (142, 145),
            51: (145, 149), 52: (149, 150), 53: (150, 154), 54: (154, 158),
            55: (158, 160), 56: (160, 165), 57: (165, 177), 58: (177, 183),
            59: (183, 184), 60: (184, 188), 61: (188, 195), 62: (195, 196),
            63: (196, 199), 64: (199, 203), 65: (203, 206), 66: (206, 210),
            67: (210, 216), 68: (216, 224), 69: (224, 231), 70: (231, 235),
            71: (235, 236), 72: (236, 247), 73: (247, 257), 74: (257, 268),
            75: (268, 274),
        },
        "restores": {
            # missing passages (scrape truncation), 1861 Wikisource wording
            17: ("end", 'If a man brandishes his sword, looks fiercely, and says, "How dare he withstand me?" - this is the valour of a common man, who can be the opponent only of a single individual. I beg your Majesty to greaten it.'),
            25: ("end", "Thus, neither of the proceedings was without a purpose. And moreover, in the spring they examined the ploughing, and supplied any deficiency of seed; in the autumn they examined the reaping, and supplied any deficiency of yield. There is the saying of the Xia dynasty - If our king do not take his ramble, what will become of our happiness? If our king do not make his excursion, what will become of our help? That ramble, and that excursion, were a pattern to the princes."),
            26: ("end", "Now, the state of things is different. A host marches in attendance on the ruler, and stores of provisions are consumed. The hungry are deprived of their food, and there is no rest for those who are called to toil. Maledictions are uttered by one to another with eyes askance, and the people proceed to the commission of wickedness. Thus the royal ordinances are violated, and the people are oppressed, and the supplies of food and drink flow away like water. The rulers yield themselves to the current, or they urge their way against it; they are wild; they are utterly lost - these things proceed to the grief of the inferior princes."),
            27: ("end", "Descending along with the current, and forgetting to return, is what I call yielding to it. Pressing up against it, and forgetting to return, is what I call urging their way against it. Pursuing the chase without satiety is what I call being wild. Delighting in wine without satiety is what I call being lost."),
        },
        "drop": [],
        # unit -> prefix to strip from the joined EN (chapter-title scrape artifact)
        "strip": {1: "Liang Hui Wang II "},
    },
    # 3: 公孙丑上
    3: {
        "assign": {
            1: (0, 1), 2: (1, 3), 3: (3, 8), 4: (8, 9), 5: (9, 10),
            6: (10, 11), 7: (11, 15), 8: (15, 23), 9: (23, 27), 10: (27, 30),
            11: (30, 34), 12: (34, 36), 13: (36, 37), 14: (37, 40),
            15: (40, 44), 16: (44, 47), 17: (47, 48), 18: (48, 54),
            19: (54, 59), 20: (59, 62), 21: (62, 66), 22: (66, 67),
            23: (67, 69), 24: (69, 69), 25: (69, 72), 26: (72, 74),
            27: (74, 77), 28: (77, 80), 29: (80, 83), 30: (83, 95),
            31: (95, 102), 32: (102, 106), 33: (106, 115), 34: (115, 118),
            35: (118, 119), 36: (119, 130), 37: (130, 133), 38: (133, 138),
            39: (138, 141), 40: (141, 142), 41: (142, 146), 42: (146, 151),
            43: (151, 156), 44: (156, 159), 45: (159, 161), 46: (161, 161),
            47: (161, 164), 48: (164, 165), 49: (165, 166), 50: (166, 167),
            51: (167, 168), 52: (168, 169), 53: (169, 170), 54: (170, 171),
            55: (171, 172), 56: (172, 176), 57: (176, 177), 58: (177, 179),
            59: (179, 181), 60: (181, 182), 61: (182, 186), 62: (186, 188),
            63: (188, 191), 64: (191, 195), 65: (195, 199), 66: (199, 201),
            67: (201, 202), 68: (202, 205), 69: (205, 206), 70: (206, 207),
            71: (207, 209), 72: (209, 210), 73: (210, 212), 74: (212, 218),
            75: (218, 227), 76: (227, 229),
        },
        "restores": {
            23: [
                ("start", "Gong Sun Chou said, 'May I venture to ask an explanation from you, Master, of how you maintain an unperturbed mind, and how the philosopher Gao does the same?' Mencius answered, 'Gao says, \"What is not attained in words is not to be sought for in the mind; what produces dissatisfaction in the mind, is not to be helped by passion-effort.\" This last, when there is unrest in the mind, not to seek for relief from passion-effort, may be conceded."),
                ("end", "The passion-nature pervades and animates the body. The will is first and chief, and the passion-nature is subordinate to it. Therefore I say, Maintain firm the will, and do no violence to the passion-nature.'"),
            ],
            24: ("end", "Chou observed, 'Since you say \"The will is chief, and the passion-nature is subordinate,\" how do you also say, \"Maintain firm the will, and do no violence to the passion-nature?\"' Mencius replied, 'When it is the will alone which is active, it moves the passion-nature. When it is the passion-nature alone which is active, it moves the will. For instance now, in the case of a man falling or running, that is from the passion-nature, and yet it moves the mind.'"),
            46: ("end", "If a prince hates disgrace, the best course for him to pursue, is to esteem virtue and honour virtuous scholars, giving the worthiest among them places of dignity, and the able offices of trust. When throughout his kingdom there is leisure and rest from external troubles, let him, taking advantage of such a season, clearly digest the principles of his government with its legal sanctions, and then even great kingdoms will be constrained to stand in awe of him."),
        },
        "drop": [],
        "strip": {},
    },
    # 4: 公孙丑下
    4: {
        "assign": {
            1: (0, 1), 2: (1, 4), 3: (4, 7), 4: (7, 12), 5: (12, 14),
            6: (14, 18), 7: (18, 21), 8: (21, 25), 9: (25, 40), 10: (40, 42),
            11: (42, 49), 12: (49, 60), 13: (60, 63), 14: (63, 65),
            15: (65, 68), 16: (68, 70), 17: (87, 92), 18: (92, 93),
            19: (93, 97), 20: (97, 100), 21: (100, 103), 22: (103, 105),
            23: (105, 108), 24: (108, 112), 25: (112, 114), 26: (114, 116),
            27: (116, 117), 28: (117, 118), 29: (118, 119), 30: (119, 121),
            31: (121, 124), 32: (124, 128), 33: (128, 133), 34: (133, 136),
            35: (136, 140), 36: (140, 141), 37: (141, 142), 38: (142, 147),
            39: (147, 157), 40: (157, 159), 41: (159, 160), 42: (160, 169),
            43: (169, 179), 44: (179, 185), 45: (185, 186), 46: (186, 191),
            47: (191, 193), 48: (193, 194), 49: (194, 196), 50: (196, 201),
            51: (201, 206), 52: (206, 207), 53: (207, 209), 54: (209, 214),
            55: (214, 217), 56: (217, 221), 57: (221, 222), 58: (223, 227),
            59: (227, 230), 60: (230, 235), 61: (235, 239), 62: (239, 240),
            63: (240, 242), 64: (242, 243), 65: (243, 244), 66: (244, 247),
            67: (247, 250), 68: (250, 252), 69: (252, 254), 70: (254, 256),
        },
        "restores": {},
        "drop": list(range(70, 87)) + [222],
        "strip": {},
    },
    # 5: 滕文公上
    5: {
        "assign": {
            1: (0, 1), 2: (1, 2), 3: (2, 5), 4: (5, 13), 5: (13, 16),
            6: (16, 19), 7: (19, 24), 8: (24, 29), 9: (29, 38), 10: (38, 42),
            11: (42, 48), 12: (48, 49), 13: (49, 51), 14: (51, 55),
            15: (58, 59), 16: (59, 69), 17: (69, 69), 18: (70, 75),
            19: (75, 76), 20: (76, 79), 21: (79, 84), 22: (84, 85),
            23: (85, 88), 24: (88, 94), 25: (94, 97), 26: (97, 98),
            27: (105, 106), 28: (106, 107), 29: (107, 110), 30: (110, 114),
            31: (114, 116), 32: (116, 120), 33: (120, 122), 34: (122, 129),
            35: (129, 145), 36: (145, 150), 37: (150, 157), 38: (157, 164),
            39: (164, 173), 40: (173, 176), 41: (176, 183), 42: (183, 184),
            43: (184, 186), 44: (186, 191), 45: (191, 198), 46: (198, 204),
            47: (204, 211), 48: (211, 214), 49: (214, 215), 50: (215, 217),
            51: (217, 220), 52: (220, 226), 53: (226, 230), 54: (230, 238),
            55: (238, 244), 56: (244, 246), 57: (246, 253), 58: (253, 255),
        },
        "restores": {
            # 助者藉也 — the corpus stream's second rendering of the 贡助彻
            # passage was truncated after its first sentence (dropped as a
            # variant duplicate); restore the missing sentence from the wiki.
            17: ("end", "The aid system means mutual dependence."),
        },
        "drop": [55, 56, 57, 69] + list(range(98, 105)),
        "strip": {},
    },
    # 6: 滕文公下
    6: {
        "assign": {
            1: (0, 4), 2: (4, 10), 3: (10, 12), 4: (12, 20), 5: (20, 24),
            6: (24, 28), 7: (28, 31), 8: (31, 38), 9: (38, 39), 10: (45, 50),
            11: (50, 51), 12: (51, 58), 13: (58, 59), 14: (59, 61),
            15: (61, 67), 16: (67, 68), 17: (68, 72), 18: (72, 74),
            19: (74, 81), 20: (81, 89), 21: (89, 92), 22: (92, 95),
            23: (95, 101), 24: (101, 106), 25: (111, 113), 26: (113, 124),
            27: (124, 129), 28: (129, 131), 29: (131, 134), 30: (134, 140),
            31: (140, 144), 32: (144, 146), 33: (146, 150), 34: (150, 154),
            35: (154, 159), 36: (159, 162), 37: (162, 165), 38: (165, 166),
            39: (166, 169), 40: (169, 170), 41: (170, 175), 42: (175, 179),
            43: (179, 183), 44: (183, 192), 45: (192, 195), 46: (195, 199),
            47: (199, 201), 48: (201, 201), 49: (201, 206), 50: (206, 207),
            51: (207, 209), 52: (209, 212), 53: (212, 213), 54: (213, 217),
            55: (217, 220), 56: (220, 226), 57: (226, 228), 58: (228, 234),
            59: (234, 234), 60: (235, 239),
        },
        "restores": {
            47: ("end", "The words of Yang Zhu and Mo Di fill the country. If you listen to people's discourses throughout it, you will find that they have adopted the views either of Yang or of Mo. Now, Yang's principle is \"each one for himself,\" which does not acknowledge the claims of the sovereign. Mo's principle is \"to love all equally,\" which does not acknowledge the peculiar affection due to a father. But to acknowledge neither king nor father is to be in the state of a beast. Gong Ming Yi said, \"In their kitchens, there is fat meat. In their stables, there are fat horses. But their people have the look of hunger, and on the wilds there are those who have died of famine. This is leading on beasts to devour men.\""),
            48: ("end", "If the principles of Yang and Mo be not stopped, and the principles of Confucius not set forth, then those perverse speakings will delude the people, and stop up the path of benevolence and righteousness. When benevolence and righteousness are stopped up, beasts will be led on to devour men, and men will devour one another."),
        },
        "drop": list(range(39, 45)) + list(range(106, 111)) + [234],
        "strip": {},
        # u58/u59 split the single sentence "…said, \"It is the flesh of that
        # cackling thing,\" upon which he went out and vomited it." at the
        # unit boundary (the Chinese itself splits there: 』出而哇之。).
        "manual": {
            58: "Mencius rejoined, 'Zhong belongs to an ancient and noble family of Qi. His elder brother Dai received from Gai a revenue of 10,000 zhong, but he considered his brother's emolument to be unrighteous, and would not eat of it, and in the same way he considered his brother's house to be unrighteous, and would not dwell in it. Avoiding his brother and leaving his mother, he went and dwelt in Wu Ling. One day afterwards, he returned to their house, when it happened that some one sent his brother a present of a live goose. He, knitting his eyebrows, said, \"What are you going to use that cackling thing for?\" By-and-by his mother killed the goose, and gave him some of it to eat. Just then his brother came into the house, and said, \"It is the flesh of that cackling thing,\"",
            59: "upon which he went out and vomited it.",
        },
    },
    # 7: 离娄上
    7: {
        "assign": {
            1: (0, 1), 2: (1, 4), 3: (4, 5), 4: (5, 7), 5: (7, 10),
            6: (10, 12), 7: (12, 14), 8: (14, 17), 9: (17, 20), 10: (20, 21),
            11: (21, 22), 12: (22, 23), 13: (23, 26), 14: (26, 28),
            15: (28, 28), 16: (28, 29), 17: (29, 32), 18: (32, 33),
            19: (33, 34), 20: (34, 35), 21: (35, 36), 22: (36, 40),
            23: (40, 41), 24: (41, 42), 25: (42, 46), 26: (46, 50),
            27: (50, 53), 28: (53, 57), 29: (57, 59), 30: (59, 60),
            31: (60, 62), 32: (62, 67), 33: (67, 70), 34: (70, 73),
            35: (73, 74), 36: (74, 77), 37: (77, 80), 38: (80, 82),
            39: (82, 86), 40: (86, 86), 41: (86, 86), 42: (86, 86),
            43: (86, 89), 44: (89, 91), 45: (91, 95), 46: (95, 96),
            47: (96, 97), 48: (97, 100), 49: (100, 105), 50: (105, 107),
            51: (107, 109), 52: (109, 115), 53: (115, 118), 54: (118, 119),
            55: (119, 122), 56: (122, 127), 57: (127, 129), 58: (129, 133),
            59: (133, 135), 60: (135, 139), 61: (151, 156), 62: (156, 158),
            63: (158, 160), 64: (160, 161), 65: (161, 168), 66: (168, 169),
            67: (169, 171), 68: (171, 177), 69: (177, 179), 70: (179, 186),
            71: (186, 187), 72: (187, 193), 73: (193, 194), 74: (194, 195),
            75: (195, 196), 76: (196, 197), 77: (197, 206), 78: (206, 207),
            79: (207, 209), 80: (209, 210), 81: (210, 212), 82: (212, 213),
            83: (213, 220), 84: (220, 223), 85: (223, 227),
        },
        "restores": {
            15: ("end", "He who as a sovereign would perfectly discharge the duties of a sovereign, and he who as a minister would perfectly discharge the duties of a minister, have only to imitate - the one Yao, and the other Shun. He who does not serve his sovereign as Shun served Yao, does not respect his sovereign; and he who does not rule his people as Yao ruled his, injures his people."),
            40: ("end", "The people turn to a benevolent rule as water flows downwards, and as wild beasts fly to the wilderness."),
            41: ("end", "Accordingly, as the otter aids the deep waters, driving the fish into them, and the hawk aids the thickets, driving the little birds to them, so Jie and Zhou aided Tang and Wu, driving the people to them."),
            42: ("end", "If among the present rulers of the kingdom, there were one who loved benevolence, all the other princes would aid him, by driving the people to him. Although he wished not to become sovereign, he could not avoid becoming so."),
        },
        "drop": list(range(139, 151)),
        "strip": {},
    },
    # 8: 离娄下
    8: {
        "assign": {
            1: (0, 1), 2: (1, 2), 3: (2, 4), 4: (4, 5), 5: (5, 6),
            6: (6, 8), 7: (8, 9), 8: (9, 10), 9: (10, 11), 10: (11, 12),
            11: (12, 14), 12: (14, 19), 13: (19, 24), 14: (24, 26),
            15: (26, 28), 16: (28, 29), 17: (29, 31), 18: (31, 32),
            19: (32, 33), 20: (33, 34), 21: (34, 35), 22: (35, 36),
            23: (36, 38), 24: (38, 43), 25: (43, 44), 26: (44, 47),
            27: (47, 48), 28: (48, 51), 29: (51, 56), 30: (56, 59),
            31: (59, 61), 32: (61, 63), 33: (63, 64), 34: (64, 65),
            35: (65, 66), 36: (66, 67), 37: (67, 69), 38: (69, 70),
            39: (70, 71), 40: (71, 73), 41: (73, 75), 42: (75, 76),
            43: (76, 79), 44: (79, 85), 45: (85, 92), 46: (92, 98),
            47: (98, 100), 48: (117, 118), 49: (118, 119), 50: (119, 120),
            51: (120, 124), 52: (124, 126), 53: (126, 127), 54: (127, 130),
            55: (130, 132), 56: (132, 133), 57: (133, 135), 58: (135, 137),
            59: (137, 139), 60: (139, 143), 61: (143, 147), 62: (147, 157),
            63: (157, 159), 64: (159, 161), 65: (161, 163), 66: (163, 165),
            67: (165, 165), 68: (165, 165), 69: (165, 165), 70: (165, 168),
            71: (168, 175), 72: (175, 176), 73: (176, 178), 74: (178, 182),
            75: (182, 189), 76: (189, 191), 77: (191, 194), 78: (194, 198),
            79: (198, 201), 80: (201, 207), 81: (207, 214), 82: (214, 215),
        },
        "restores": {
            # u66 tail: 是以如是其急也
            66: ("end", "It was on this account that they were so earnest."),
            67: ("end", "If Yu and Ji, and Yanzi, had exchanged places, each would have done what the other did."),
            68: ("end", "Here now in the same apartment with you are people fighting - you ought to part them. Though you part them with your cap simply tied over your unbound hair, your conduct will be allowable."),
            69: ("end", "If the fighting be only in the village or neighbourhood, if you go to put an end to it with your cap tied over your hair unbound, you will be in error. Although you should shut your door in such a case, your conduct will be allowable."),
        },
        "drop": list(range(100, 117)),
        "strip": {},
        # E161 is a split stub ("Mencius said, '") - glue to E162 without space.
        "manual": {65: "Mencius said, 'Yu, Ji, and Yan Hui agreed in the principle of their conduct."},
    },
    # 9: 万章上
    9: {
        "assign": {
            1: (0, 0), 2: (0, 2), 3: (2, 7), 4: (7, 10), 5: (10, 15),
            6: (15, 21), 7: (21, 28), 8: (28, 30), 9: (30, 45), 10: (45, 48),
            11: (48, 58), 12: (58, 61), 13: (61, 65), 14: (65, 67),
            15: (67, 74), 16: (74, 80), 17: (80, 90), 18: (90, 95),
            19: (95, 99), 20: (99, 103), 21: (103, 108), 22: (108, 111),
            23: (111, 114), 24: (114, 117), 25: (117, 118), 26: (118, 121),
            27: (121, 129), 28: (129, 135), 29: (135, 142), 30: (142, 143),
            31: (143, 144), 32: (144, 153), 33: (153, 158), 34: (158, 161),
            35: (161, 163), 36: (163, 165), 37: (165, 171), 38: (171, 172),
            39: (172, 175), 40: (175, 177), 41: (177, 181), 42: (181, 184),
            43: (184, 187), 44: (187, 190), 45: (190, 192), 46: (192, 195),
            47: (195, 197), 48: (197, 199), 49: (199, 201), 50: (201, 206),
            51: (206, 210), 52: (210, 212), 53: (219, 222), 54: (222, 225),
            55: (225, 231), 56: (231, 232),
        },
        "restores": {
            1: ("end", "Wan Zhang asked Mencius, saying, 'When Shun went into the fields, he cried out and wept towards the pitying heavens. Why did he cry out and weep?' Mencius replied, 'He was dissatisfied, and full of earnest desire.'"),
            2: ("start", "Wan Zhang said, 'When his parents love him, a son rejoices and forgets them not. When his parents hate him, though they punish him, he does not murmur. Was Shun then murmuring against his parents?'"),
            4: ("start", "The Di caused his own children, nine sons and two daughters, the various officers, oxen and sheep, storehouses and granaries, all to be prepared, to serve Shun amid the channelled fields."),
        },
        "drop": [4, 5] + list(range(211, 219)),
        "strip": {},
    },
    # 10: 万章下
    10: {
        "assign": {
            1: (0, 7), 2: (7, 15), 3: (15, 23), 4: (23, 26), 5: (26, 27),
            6: (27, 32), 7: (32, 34), 8: (34, 35), 9: (35, 37), 10: (37, 39),
            11: (39, 45), 12: (45, 46), 13: (46, 47), 14: (47, 48),
            15: (48, 49), 16: (49, 53), 17: (53, 54), 18: (54, 57),
            19: (57, 57), 20: (57, 57), 21: (57, 59), 22: (59, 62),
            23: (62, 64), 24: (64, 68), 25: (68, 70), 26: (70, 74),
            27: (74, 80), 28: (80, 81), 29: (81, 87), 30: (87, 91),
            31: (91, 93), 32: (98, 99), 33: (99, 101), 34: (101, 105),
            35: (105, 107), 36: (107, 111), 37: (111, 115), 38: (115, 120),
            39: (120, 126), 40: (126, 130), 41: (130, 132), 42: (132, 135),
            43: (135, 137), 44: (137, 141), 45: (142, 148), 46: (148, 149),
            47: (149, 154), 48: (154, 157), 49: (157, 158), 50: (158, 158),
            51: (158, 162), 52: (162, 165), 53: (165, 168), 54: (168, 176),
            55: (176, 177), 56: (177, 179), 57: (179, 181),
        },
        "restores": {
            18: ("end", "With those five men Xian maintained a friendship, because they thought nothing about his family. If they had thought about his family, he would not have maintained his friendship with them."),
            19: ("end", "Not only has the chief of a family of a hundred chariots acted thus. The same thing was exemplified by the sovereign of a small State. The duke Hui of Bi said, \"I treat Zi Si as my Teacher, and Yan Ban as my Friend. As to Wang Shun and Chang Xi, they serve me.\""),
            20: ("end", "Not only has the sovereign of a small State acted thus. The same thing has been exemplified by the sovereign of a large State. There was the duke Ping of Jin with Hai Tang - when Tang told him to come into his house, he came; when he told him to be seated, he sat; when he told him to eat, he ate. There might only be coarse rice and soup of vegetables, but he always ate his fill, not daring to do otherwise. Here, however, he stopped, and went no farther. He did not call him to share any of Heaven's places, or to govern any of Heaven's offices, or to partake of any of Heaven's emoluments. His conduct was but a scholar's honouring virtue and talents, not the honouring them proper to a king or a duke."),
            49: ("end", "If a common man were summoned with the article appropriate to the summoning of a scholar, how could he presume to go? How much more may we expect this refusal to go, when a man of talents and virtue is summoned in a way which is inappropriate to his character!"),
            50: ("end", "When a prince wishes to see a man of talents and virtue, and does not take the proper course to get his wish, it is as if he wished him to enter his palace, and shut the door against him. Now, righteousness is the way, and propriety is the door, but it is only the superior man who can follow this way, and go out and in by this door. It is said in the Book of Poetry, \"The way to Zhou is level like a whetstone, And straight as an arrow. The officers tread in it, And the mean men look at it.\""),
        },
        "drop": [55, 141] + list(range(93, 98)),
        "strip": {},
    },
    # 11: 告子上
    11: {
        "assign": {
            1: (0, 2), 2: (2, 7), 3: (7, 10), 4: (10, 13), 5: (13, 16),
            6: (16, 17), 7: (21, 25), 8: (25, 27), 9: (27, 29), 10: (29, 34),
            11: (34, 37), 12: (37, 40), 13: (40, 42), 14: (42, 44),
            15: (44, 45), 16: (45, 50), 17: (50, 58), 18: (58, 60),
            19: (60, 61), 20: (61, 62), 21: (62, 66), 22: (66, 68),
            23: (68, 71), 24: (71, 72), 25: (72, 79), 26: (79, 80),
            27: (80, 84), 28: (84, 87), 29: (87, 89), 30: (89, 91),
            31: (91, 93), 32: (93, 98), 33: (98, 100), 34: (100, 103),
            35: (103, 108), 36: (108, 113), 37: (113, 118), 38: (118, 119),
            39: (119, 121), 40: (121, 125), 41: (125, 126), 42: (126, 129),
            43: (129, 138), 44: (138, 142), 45: (142, 144), 46: (144, 146),
            47: (146, 147), 48: (147, 150), 49: (150, 151), 50: (151, 154),
            51: (154, 159), 52: (159, 160), 53: (160, 161), 54: (161, 162),
            55: (162, 163), 56: (163, 165), 57: (165, 167), 58: (167, 171),
            59: (171, 174), 60: (174, 176), 61: (176, 176), 62: (176, 176),
            63: (176, 176), 64: (176, 177), 65: (177, 179), 66: (179, 187),
            67: (187, 190), 68: (190, 191), 69: (191, 193), 70: (193, 196),
            71: (196, 198), 72: (198, 201), 73: (201, 204), 74: (204, 205),
            75: (205, 207), 76: (207, 208), 77: (208, 209),
        },
        "restores": {
            60: ("end", "He who nourishes the little belonging to him is a little man, and he who nourishes the great is a great man."),
            61: ("end", "Here is a plantation-keeper, who neglects his wu and jia, and cultivates his sour jujube-trees; he is a poor plantation-keeper."),
            62: ("end", "He who nourishes one of his fingers, neglecting his shoulders or his back, without knowing that he is doing so, is a man who resembles a hurried wolf."),
            63: ("end", "A man who only eats and drinks is counted mean by others; because he nourishes what is little to the neglect of what is great."),
        },
        "drop": [17, 18, 19, 20, 69],
        "strip": {},
    },
    # 12: 告子下
    12: {
        "assign": {
            1: (0, 2), 2: (2, 3), 3: (3, 4), 4: (4, 6), 5: (6, 7),
            6: (7, 8), 7: (8, 11), 8: (11, 13), 9: (13, 14), 10: (14, 18),
            11: (18, 25), 12: (25, 30), 13: (30, 32), 14: (32, 34),
            15: (34, 38), 16: (38, 41), 17: (41, 49), 18: (49, 50),
            19: (50, 54), 20: (54, 56), 21: (56, 57), 22: (57, 59),
            23: (59, 62), 24: (62, 66), 25: (66, 69), 26: (69, 73),
            27: (73, 75), 28: (75, 77), 29: (77, 79), 30: (79, 82),
            31: (82, 83), 32: (83, 84), 33: (84, 88), 34: (88, 96),
            35: (96, 99), 36: (99, 102), 37: (102, 109), 38: (109, 115),
            39: (115, 118), 40: (118, 124), 41: (124, 126), 42: (126, 135),
            43: (135, 140), 44: (140, 142), 45: (142, 143), 46: (143, 145),
            47: (145, 146), 48: (146, 147), 49: (147, 150), 50: (150, 150),
            51: (150, 150), 52: (150, 151), 53: (151, 152), 54: (152, 155),
            55: (155, 158), 56: (158, 159), 57: (159, 161), 58: (161, 162),
            59: (162, 165), 60: (165, 168), 61: (168, 170), 62: (170, 171),
            63: (171, 173), 64: (173, 174), 65: (174, 176), 66: (176, 177),
            67: (177, 180), 68: (180, 184), 69: (184, 186), 70: (186, 192),
            71: (192, 192), 72: (192, 192), 73: (192, 193), 74: (193, 194),
            75: (194, 195), 76: (198, 203), 77: (203, 205), 78: (205, 206),
            79: (206, 207), 80: (207, 211), 81: (211, 212), 82: (212, 217),
            83: (217, 220), 84: (220, 221), 85: (221, 222), 86: (229, 231),
        },
        "restores": {
            49: ("end", "The territory appropriated to a Hou is 100 li square. Without 100 li, he would not have sufficient wherewith to observe the statutes kept in his ancestral temple."),
            50: ("end", "When Zhou Gong was invested with the principality of Lu, it was a hundred li square. The territory was indeed enough, but it was not more than 100 li. When Tai Gong was invested with the principality of Qi, it was 100 li square. The territory was indeed enough, but it was not more than 100 li."),
            51: ("end", "Now Lu is five times 100 li square. If a true royal ruler were to arise, whether do you think that Lu would be diminished or increased by him?"),
            71: ("end", "What then made you so glad that you could not sleep?'"),
            72: ("end", "He is a man who loves what is good."),
        },
        "drop": list(range(195, 198)) + list(range(222, 229)),
        "strip": {},
    },
    # 13: 尽心上
    13: {
        "assign": {
            1: (0, 2), 2: (2, 3), 3: (3, 4), 4: (4, 5), 5: (5, 6),
            6: (6, 7), 7: (7, 9), 8: (9, 10), 9: (10, 11), 10: (11, 12),
            11: (12, 13), 12: (13, 14), 13: (14, 15), 14: (15, 17),
            15: (17, 18), 16: (18, 19), 17: (19, 20), 18: (20, 25),
            19: (25, 26), 20: (26, 29), 21: (29, 30), 22: (30, 31),
            23: (31, 32), 24: (32, 36), 25: (36, 38), 26: (38, 40),
            27: (40, 42), 28: (42, 44), 29: (44, 47), 30: (47, 50),
            31: (50, 51), 32: (51, 52), 33: (52, 54), 34: (54, 55),
            35: (55, 56), 36: (56, 59), 37: (59, 61), 38: (61, 62),
            39: (62, 63), 40: (63, 65), 41: (65, 66), 42: (66, 67),
            43: (67, 69), 44: (69, 71), 45: (71, 72), 46: (72, 73),
            47: (73, 74), 48: (74, 75), 49: (75, 76), 50: (76, 77),
            51: (77, 78), 52: (78, 79), 53: (79, 82), 54: (82, 89),
            55: (89, 92), 56: (92, 96), 57: (96, 97), 58: (97, 98),
            59: (98, 101), 60: (101, 104), 61: (104, 107), 62: (107, 109),
            63: (109, 110), 64: (110, 111), 65: (111, 112), 66: (112, 114),
            67: (114, 115), 68: (115, 117), 69: (117, 121), 70: (121, 125),
            71: (125, 126), 72: (126, 127), 73: (127, 129), 74: (129, 130),
            75: (130, 133), 76: (133, 134), 77: (134, 137), 78: (137, 139),
            79: (142, 147), 80: (147, 148), 81: (148, 149), 82: (149, 155),
            83: (155, 159), 84: (159, 160), 85: (160, 161), 86: (161, 162),
            87: (162, 164), 88: (164, 165), 89: (165, 168), 90: (168, 171),
 91: (171, 171), 92: (171, 174), 93: (174, 178), 94: (178, 180),
            95: (180, 181), 96: (181, 182), 97: (182, 184), 98: (184, 186),
            99: (186, 188), 100: (188, 190), 101: (190, 193), 102: (193, 194),
            103: (194, 195), 104: (195, 196), 105: (196, 197), 106: (197, 198),
            107: (198, 199), 108: (199, 201), 109: (201, 203), 110: (203, 205),
            111: (205, 206), 112: (206, 208), 113: (208, 210), 114: (210, 212),
            115: (212, 214), 116: (214, 215), 117: (215, 219), 118: (219, 220),
            119: (220, 224),
        },
        "restores": {},
        "drop": list(range(139, 142)) + [171],
        "manual": {
            91: "Mencius said,",
            92: "'The residence, the carriages and horses, and the dress of the king's son, are mostly the same as those of other men. That he looks so is occasioned by his position. How much more should a peculiar air distinguish him whose position is in the wide house of the world!",
        },
        "strip": {},
    },
    # 14: 尽心下
    14: {
        "assign": {
            1: (0, 3), 2: (3, 7), 3: (7, 9), 4: (9, 11), 5: (11, 12),
            6: (12, 13), 7: (13, 15), 8: (15, 17), 9: (17, 18), 10: (18, 21),
            11: (21, 22), 12: (22, 26), 13: (26, 28), 14: (28, 29),
            15: (29, 31), 16: (31, 34), 17: (34, 35), 18: (35, 36),
            19: (36, 38), 20: (38, 39), 21: (39, 40), 22: (40, 41),
            23: (41, 42), 24: (42, 43), 25: (43, 44), 26: (44, 45),
            27: (45, 46), 28: (46, 47), 29: (47, 48), 30: (48, 54),
            31: (54, 56), 32: (56, 58), 33: (58, 59), 34: (59, 60),
            35: (60, 62), 36: (62, 66), 37: (66, 68), 38: (68, 70),
            39: (70, 71), 40: (71, 73), 41: (73, 75), 42: (75, 77),
            43: (77, 83), 44: (83, 85), 45: (85, 88), 46: (88, 90),
            47: (90, 91), 48: (91, 92), 49: (92, 93), 50: (93, 94),
            51: (94, 95), 52: (95, 96), 53: (96, 97), 54: (97, 98),
            55: (98, 100), 56: (100, 101), 57: (101, 105), 58: (105, 107),
            59: (107, 111), 60: (111, 113), 61: (113, 118), 62: (118, 120),
            63: (120, 122), 64: (122, 123), 65: (123, 124), 66: (124, 127),
            67: (127, 128), 68: (128, 129), 69: (129, 130), 70: (130, 134),
            71: (134, 134), 72: (134, 134), 73: (134, 134), 74: (134, 137),
            75: (137, 138), 76: (138, 144), 77: (144, 148), 78: (148, 151),
            79: (151, 152), 80: (152, 153), 81: (153, 154), 82: (154, 157),
            83: (157, 158), 84: (158, 162), 85: (162, 168), 86: (168, 171),
            87: (171, 179), 88: (179, 186), 89: (186, 188), 90: (188, 190),
            91: (190, 192), 92: (192, 194), 93: (194, 198),
        },
        "restores": {
            71: ("end", "The superior man executes the law, and so waits merely for what is appointed."),
            72: ("end", "Mencius said, 'Those who give counsel to the great should despise them, and not look at their pomp and display."),
            73: ("end", "Halls several times eight cubits high, with beams projecting several cubits; these, if my wishes were to be realized, I would not have. Food spread before me over ten cubits square, and attendants and concubines to the amount of hundreds; these, though my wishes were realized, I would not have. Pleasure and wine, and the dash of hunting, with thousands of chariots following after me; these, though my wishes were realized, I would not have. What they esteem are what I would have nothing to do with; what I esteem are the rules of the ancients. Why should I stand in awe of them?'"),
        },
        "drop": [],
        "strip": {},
    },
}


def en_fragments(t):
    segs = []
    buf = ""
    i = 0
    while i < len(t):
        ch = t[i]
        buf += ch
        if ch in ".!?":
            while i + 1 < len(t) and t[i + 1] in "'\"":
                i += 1
                buf += t[i]
            segs.append(buf)
            buf = ""
        i += 1
    if buf.strip():
        segs.append(buf)
    return segs


def zh_segments(t):
    segs = []
    buf = ""
    i = 0
    while i < len(t):
        ch = t[i]
        buf += ch
        if ch in "。！？":
            while i + 1 < len(t) and t[i + 1] in "」』":
                i += 1
                buf += t[i]
            segs.append(buf)
            buf = ""
        i += 1
    if buf.strip():
        segs.append(buf)
    return segs


def join_fragments(frags):
    out = ""
    for f in frags:
        f = f.strip()
        if not f:
            continue
        if f.startswith("-"):
            f = f[1:].strip()
        f = re.sub(r'"\s+([A-Z])', r'"\1', f)
        if out and f and f[0] in ".!?":
            out += f
        elif out:
            out += " " + f
        else:
            out = f
    return out


def load(chapter):
    with open(f"{CONTENT}/chapter-{chapter:03d}.json") as f:
        return json.load(f)["chapter"]


def global_streams(units):
    ge = []
    for u in units:
        tr = u.get("canonical_translations") or []
        if tr:
            for s in en_fragments(tr[0]["text"]):
                ge.append((u["order"], s))
    return ge


def workbench(chapter):
    ch = load(chapter)
    units = ch["reading_units"]
    ge = global_streams(units)
    print(f"=== chapter {chapter}: {len(units)} units, {len(ge)} EN fragments ===")
    print("\n--- GLOBAL EN FRAGMENTS ---")
    for k, (uo, s) in enumerate(ge):
        print(f"E{k:>3} [u{uo}]: {s.strip()}")
    print("\n--- UNITS ---")
    for u in units:
        segs = zh_segments(u["text"])
        cur = (u.get("canonical_translations") or [{}])[0].get("text", "")
        cf = en_fragments(cur)
        print(f"\nu{u['order']:>3} ({len(segs)} segs / {len(cf)} EN frags):")
        for s in segs:
            print(f"    Z: {s}")
        print(f"   cur EN: {cur[:100]!r}")


def apply_chapter(chapter):
    tbl = TABLES[chapter]
    ch = load(chapter)
    units = ch["reading_units"]
    ge = global_streams(units)
    N = len(ge)
    assign = tbl["assign"]
    drop = tbl.get("drop", [])

    used = [False] * N
    for unit, (lo, hi) in assign.items():
        assert unit == units[unit - 1]["order"], f"ch{chapter} u{unit} order mismatch"
        for k in range(lo, hi):
            if k in drop:
                continue
            assert not used[k], f"ch{chapter} fragment E{k} assigned twice"
            used[k] = True
    for k in drop:
        assert not used[k], f"ch{chapter} drop E{k} unexpectedly assigned"
    unused = [k for k in range(N) if not used[k]]
    assert unused == sorted(drop), f"ch{chapter} unused {unused} != drop {drop}"

    new_en = {}
    for unit, (lo, hi) in assign.items():
        new_en[unit] = join_fragments([ge[k][1] for k in range(lo, hi) if k not in drop])
    for unit, spec in tbl.get("restores", {}).items():
        items = spec if isinstance(spec, list) else [spec]
        for pos, text in items:
            if pos == "start":
                new_en[unit] = f"{text} {new_en[unit]}".strip()
            elif pos == "end":
                new_en[unit] = f"{new_en[unit]} {text}".strip()
    for unit, prefix in tbl.get("strip", {}).items():
        if new_en[unit].startswith(prefix):
            new_en[unit] = new_en[unit][len(prefix):].strip()
    for unit, text in tbl.get("manual", {}).items():
        new_en[unit] = text

    for u in units:
        tr = u.get("canonical_translations")
        if tr and tr[0].get("text") is not None:
            tr[0]["text"] = new_en[u["order"]]

    with open(f"{CONTENT}/chapter-{chapter:03d}.json", "w") as f:
        json.dump({"chapter": ch}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"chapter {chapter}: applied ({len(assign)} units)")


if __name__ == "__main__":
    cmd, chapter = sys.argv[1], int(sys.argv[2])
    if cmd == "workbench":
        workbench(chapter)
    elif cmd == "apply":
        apply_chapter(chapter)
    else:
        sys.exit("usage: realign_mengzi.py workbench|apply <chapter>")
