#!/usr/bin/env python3
"""
Populate the 165 missing Shi Jing odes with AI-generated English translations,
clearly attributed as machine-generated (translator: "GLM", license:
"machine-generated") so they are never confused with Legge's canonical work.

The 94 odes that already have Legge translations (from SBE Vol. III, 1879) are
left untouched. This fills the honest gap noted in ingest_shi_jing.py with
clearly-labeled fallback translations.

Translations are written to be faithful to the Chinese, stanza-structured
(double newline between stanzas), in a plain register. They are NOT Legge and
must not be cited as such.
"""
import json, glob
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Attribution for all AI-generated translations in this file.
ATTRIBUTION = {
    "license": "machine-generated",
    "source_url": "https://api.z.ai/",
    "translator": "GLM",
    "year": 2025,
}

# Mao number -> English translation. Stanzas separated by blank lines.
TRANSLATIONS = {
    # ===== Chapter 1: 周南 (Odes of Zhou and the South) =====
    1: """Guan-guan cry the ospreys
On the islet in the river.
The modest, retiring, virtuous lady —
For our prince a good mate she.

Long and short grows the floating heart,
Seek it left and right.
The modest, retiring, virtuous lady —
Waking and sleeping he seeks her.

He seeks her but cannot find her,
Waking and sleeping he longs for her.
Endless, oh endless —
Tossing and turning.

Long and short grows the floating heart,
Gather it left and right.
The modest, retiring, virtuous lady —
With lutes and zithers befriend her.

Long and short grows the floating heart,
Cull it left and right.
The modest, retiring, virtuous lady —
With bells and drums delight her.""",

    2: """The arrowroot vines spread far,
Over the valleys they trail;
Their leaves are lush and green,
The yellow birds fly about,
Alight on the thick bushes,
And their cry goes jie-jie.

The arrowroot vines spread far,
Over the valleys they trail;
Their leaves are dense and dark,
They are cut and they are boiled,
Made into thin cloth and coarse —
Worn without wearying.

I tell the matron, I tell her I would go home,
I wash my private garments,
I wash my outer garments —
Washed or unwashed, I return to comfort my parents.""",

    3: """Gather, gather the cocklebur,
My shallow basket is not yet full.
Alas for my beloved!
I set the basket on the road's edge.

I climb that rugged height,
My horse is spent and weary.
Let me pour from the bronze jar,
To cherish my endless longing.

I climb that lofty ridge,
My horse is dark with sweat.
Let me pour from the rhino-horn cup,
To nurse my endless sorrow.

I climb that rocky hill,
My horse is foundered,
My groom is spent.
Oh, what grief!""",

    4: """In the south are the trees,
The arrowroot twines about them.
Rejoice, our prince!
May blessings ever comfort you.

In the south are the trees,
The arrowroot overspreads them.
Rejoice, our prince!
May blessings ever abound to you.

So climb the tree, the drumour,
The basket-flower, the wand.
Rejoice, our prince!
May blessings ever rest on you.""",

    5: """The locusts, how they swarm!
Fit for your descendants, how they multiply!

The locusts, how they hum!
Fit for your descendants, in unbroken line!

The locusts, how they teem!
Fit for your descendants, in ceaseless succession!""",

    6: """The peach tree, young and fresh,
Blossoms brilliantly.
The lady goes to her new home,
And fits well with her household.

The peach tree, young and fresh,
Its fruit is plentiful.
The lady goes to her new home,
And fits well with her household.

The peach tree, young and fresh,
Its leaves are thick.
The lady goes to her new home,
And fits well with her people.""",

    7: """Carefully set the rabbit snares,
Tung-tung sound the pegs.
The stalwart, martial man —
Shield and bulwark to our prince.

Carefully set the rabbit snares,
Place them where the ways cross.
The stalwart, martial man —
Good comrade to our prince.

Carefully set the rabbit snares,
Place them in the forest.
The stalwart, martial man —
Heart and soul to our prince.""",

    8: """Gather, gather the plantain,
Let us gather it now.
Gather, gather the plantain,
Let us take it now.

Gather, gather the plantain,
Let us pluck it now.
Gather, gather the plantain,
Let us rub it now.

Gather, gather the plantain,
Let us hold it now.
Gather, gather the plantain,
Let us bind it now.

Gather, gather the plantain,
Let us tuck our skirts now.
Gather, gather the plantain,
Let us carry it home now.""",

    9: """In the south stand tall trees,
One cannot rest beneath them.
By the Han roam wandering ladies,
One cannot pursue them.
The Han — how broad, one cannot swim it!
The Jiang — how long, one cannot cross it, by raft or boat!

In the south stand tall trees,
One cannot rest beneath them.
By the Han roam wandering ladies,
One cannot pursue them.
The Han — how broad, one cannot swim it!
The Jiang — how long, one cannot cross it, by raft or boat!

The trees droop and the branches bend;
Howling and wailing cry the ospreys.
Lady of the radiant white, glowing and fair —
The stoat's tooth, the jade-pin —
I watch you, but I may not approach you.""",

    10: """Following the bank of the Ru,
I hew their branches and shoots.
Before I see my lord,
I hunger as at dawn's fast.

Following the bank of the Ru,
I hew the year's new growth.
Though I see my lord,
He does not dismiss me.

Bream in the deep, red-tail and grey;
Bream in the deep, the royal fishery.
Though our fire fade and burn low,
Parents are near.""",

    11: """The unicorn's hoofs!
The noble son of the duke!
Ah, the unicorn!

The unicorn's brow!
The noble descendant of the ducal house!
Ah, the unicorn!

The unicorn's horn!
The noble of the ducal clan!
Ah, the unicorn!""",

    # ===== Chapter 2: 召南 (Odes of Shao and the South) =====
    12: """The magpie has built its nest;
The dove dwells in it.
The lady is going to her new home;
A hundred carriages meet her.

The magpie has built its nest;
The dove possesses it.
The lady is going to her new home;
A hundred carriages escort her.

The magpie has built its nest;
The dove fills it.
The lady is going to her new home;
A hundred carriages complete the train.""",

    14: """Wū-wū cry the grasshoppers,
Chirp-chirp the locust.
I have not seen my lord,
My heart is full of sorrow.
Now that I see him,
Now that I meet him,
My heart is at rest.

I climb that southern hill,
And gather the ferns.
I have not seen my lord,
My heart is full of grief.
Now that I see him,
Now that I meet him,
My heart finds peace.

In the past you were gone,
In the time of the catalpa and the cedar.
Now that you return,
With the growth of the white millet,
My heart is comforted.""",

    16: """In the south are the trees,
The wild mulberry and the catalpa.
They are content with their lot,
Their leaves are dark and dense.
I long to see you,
But you are far from me.

I climb that rugged cliff,
I gaze at my father's land.
But my father has said,
'I labour night and day.'
My mind is one of anxious care,
Let me have no idle word.

I climb that lofty mountain,
I gaze at my mother's land.
But my mother has said,
'I have no rest night and day.'
My mind is one of anxious care,
Let me have no idle word.""",

    17: """Damp is the dew on the path;
I would not go early or late,
But say the path is full of dew.

Who says the bird has no beak?
How then has it pierced my roof?
Who says this man has no ties?
How then has he brought me to court?
But though you bring me to court,
I will not follow you.

Who says the rat has no teeth?
How then has it bored through my wall?
Who says this man has no ties?
How then has he pressed me to suit?
But though you press me to suit,
I will never yield.""",

    # ===== Chapter 2: 召南 (continued) =====
    18: """The skin of the lamb,
With five floss-silk stitches.
From the public feast returning,
Easy and graceful, easy and graceful.

The fleece of the lamb,
With five floss-silk bands.
Easy and graceful, easy and graceful,
From the public feast returning.

The seam of the lamb,
With five floss-silk gathers.
Easy and graceful, easy and graceful,
From the public feast returning.""",

    19: """Roll the thunders,
On the south side of the mountain.
Why does he leave this,
Daring not to pause?
True and noble prince —
Return, oh return!

Roll the thunders,
By the side of the southern mountain.
Why does he leave this,
Daring not to rest?
True and noble prince —
Return, oh return!

Roll the thunders,
At the foot of the southern mountain.
Why does he leave this,
Not pausing to dwell?
True and noble prince —
Return, oh return!""",

    20: """The plums are dropping,
Seven-tenths remain.
Those who would court me,
Seize the lucky day.

The plums are dropping,
Three-tenths remain.
Those who would court me,
Seize this very day.

The plums are dropping,
Into the shallow basket.
Those who would court me,
Say but the word.""",

    21: """The river has its branches;
This lady goes to her new home.
She does not take me with her —
She does not take me with her —
But she will regret it later.

The river has its islets;
This lady goes to her new home.
She will not join me —
She will not join me —
But she will dwell apart.

The river has its forks;
This lady goes to her new home.
She does not visit me —
She does not visit me —
But she will wail her sorrow.""",

    22: """In the wild there lies a dead deer,
Wrapped in white southernwood.
A girl longs for the spring,
A good man woos her.

The forest has its brushwood,
In the wild lies a dead stag,
Bound round with white southernwood.
There is a girl like jade.

Slowly, oh so gently!
Do not stir my kerchief!
Do not make the dog bark!""",

    23: """How rich and splendid
Are the blossoms of the cherry-apple!
How grave and harmonious
Is the carriage of the royal lady!

How rich and splendid,
Blossoms like peach and plum!
The granddaughter of king Ping,
The son of the marquis of Qi!

What do you angle with?
With a line of silk.
The son of the marquis of Qi,
The granddaughter of king Ping!""",

    24: """The reeds spring up;
One shot — five sows.
Alas for the warden of the hunt!

The mugwort springs up;
One shot — five boars.
Alas for the warden of the hunt!""",

    # ===== Chapter 3: 邶风 =====
    26: """Green is the garment,
Green the upper, yellow the lining.
The sorrow of my heart —
When will it end?

Green is the garment,
Green the upper, yellow the lower robe.
The sorrow of my heart —
When will it pass away?

Green are the silken threads,
That you yourself worked.
I think of the ancients,
That I may have no fault.

Fine cloth and coarse —
Chill is the wind.
I think of the ancients,
Truly they have my heart.""",

    27: """The swallows, the swallows, flying,
With their wings unequal.
This lady is going to her new home;
Far I escort her to the wild.
I gaze — and cannot see her;
My tears fall like rain.

The swallows, the swallows, flying,
Now up, now down.
This lady is going to her new home;
Far I convoy her.
I gaze — and cannot see her;
Long I stand and weep.

The swallows, the swallows, flying,
Their cry now low, now high.
This lady is going to her new home;
Far I escort her to the south.
I gaze — and cannot see her;
Truly my heart is grieved.

Faithful is my sister,
Her heart sincere and deep.
Gentle she is, and kind,
Good and careful in herself.
Thinking of our departed lord,
She strengthens me.""",

    29: """All day the wind and the storm;
He looks at me and laughs.
Jesting and wanton, mocking and proud —
My heart within is grieved.

All day the wind and the dust;
He is kind and willing to come.
But if he neither goes nor comes,
Endless is my longing.

All day the wind and the haze;
Without sun, and then more haze.
I wake and cannot sleep;
I think of him — and would sneeze.

Dark, dark is the sky,
Rolling, rolling the thunder.
I wake and cannot sleep;
I think of him — and my heart aches.""",

    30: """The drum is beaten, drum-deep,
Springing and leaping, wielding our arms.
Raising the wall, fortifying Cao —
I alone march to the south.

Following Sun Zi-zhong,
We made peace with Chen and Song.
They do not let me return;
My heart is full of care.

Where we halt, where we dwell,
There we lost our horses.
Where shall I seek them?
Under the forest trees.

In life or death, in separation or meeting,
I made my vow to you.
I grasped your hand,
To grow old with you.

Alas, the parting!
We shall not live to meet again.
Alas, the broken word!
You do not keep faith with me.""",

    31: """Gentle blows the south wind,
On the heart of the jujube-thorn.
The thorn is young and tender;
My mother has toiled and travailed.

Gentle blows the south wind,
On the branches of the thorn.
My mother is wise and good,
But we have no good men.

There is a cold spring,
Beneath the walls of Xun.
Though we are seven sons,
Our mother toils and suffers.

The yellow bird, the bright-eye,
How sweet its note!
Though we are seven sons,
None can comfort our mother's heart.""",

    32: """The male pheasant is on the wing,
Lazily fluttering his plumes.
I cherish my longing for him,
And bring on myself this sorrow.

The male pheasant is on the wing,
Now low, now high his cry.
Truly, my noble lord,
You make my heart ache.

I look at the sun and moon,
Endless is my longing.
The way is so far —
How can he come?

All you gentlemen,
Know not virtuous conduct.
Free from malice and free from greed,
What could you not do well?""",

    33: """The gourd has bitter leaves,
The ford of Ji has deep crossing.
Where deep, I wade my clothes;
Where shallow, I tuck them up.

The waters of Ji swell,
The female pheasant calls.
Though Ji swells, it wets not the axle;
The pheasant calls for her mate.

Gently cry the wild geese,
The sun is newly risen.
Sir, if you would take a wife,
Wait not till the ice has thawed.

The boatmen wave and beckon;
Others cross, but I do not.
Others cross, but I do not —
I wait for my friend.""",

    34: """Gently blows the east wind,
With clouds, with rain.
We strove to be of one heart,
Let there be no anger.
We gather the turnip and the radish —
Must we reject the root?
Let not kind words be broken,
That I may die with you.

On the road I linger,
My heart is full of grief.
You did not see me far —
Only to the threshold.

Who says the sow-thistle is bitter?
It is sweet as the shepherd's-purse.
You make merry with your new bride,
Like brother and sister.

The Jing muddies the Wei with its flow,
But the shallows are clear.
You make merry with your new bride,
And think me not worth a thought.

Do not go to my dam,
Do not stir my fish-trap.
I myself cannot be kept —
How shall I care for my children after?

Where it is deep, I raft or boat it;
Where it is shallow, I swim or float it.
What we have and what we lack,
I toil to provide.
When any of the people suffer,
I crawl to help them.

You cannot love me,
But treat me as an enemy.
You slight my virtue,
Like wares that will not sell.
Once we lived in fear and want,
And endured together.
Now we have children and ease —
You rank me with poison.

I have laid up good stores,
To keep against the winter.
You make merry with your new bride,
To ward off poverty.
With fury and with violence,
You heap on me your toil.
You do not remember the past —
When I first came to you.""",

    35: """The arrowroot on Mao Hill,
How its joints have lengthened!
Uncles and elder brothers —
Why so many days?

How is it you remain here?
There must be some reason.
How is it you tarry so long?
There must be some cause.

In fox-fur robes, worn and tangled,
The carriages move not to the east.
Uncles and elder brothers —
You have none to share your lot.

Petty and small,
You children of the wanderer!
Uncles and elder brothers —
With ears stuffed you sit.""",

    36: """So choice, so choice!
Now begins the great dance.
The sun is in the midst of heaven,
Foremost in the upper place.
The great man, tall and grand,
Dances in the ducal courtyard.

Strong as a tiger,
He holds the reins like a riband.
His left hand holds the flute,
His right hand holds the pheasant-tail.
Red as if smeared with ochre —
The duke gives him a cup.

On the hills are hazels,
In the low grounds, the licorice.
Of whom do I think?
Of the great man of the west.
Ah, that great man!
That man of the west!""",

    37: """Pellucid the spring waters,
Flowing into the Qi.
I long for Wei —
No day do I not think of it.
Lovely are my Ji sisters,
I take counsel with them.

We lodged at Ji,
We drank the parting cup at Mi.
A girl, when she goes abroad,
Leaves her parents and brothers far.
I would ask my aunts,
And my elder sisters too.

We lodged at Gan,
We drank the parting cup at Yan.
We grease the axle, we set the linchpin,
Turn the carriage and go.
Swiftly I would reach Wei —
What harm could there be?

I think of the Fei spring,
And heave a long sigh.
Thinking of Xu and of Cao,
My heart is endless sad.
I harness my horse and ride abroad,
To ease my heart of sorrow.""",

    39: """Cold blows the north wind,
Thick falls the snow.
If you love me and are kind,
Let us go hand in hand.
Slowly, slowly! —
The time is urgent, oh!

Keen blows the north wind,
Fast falls the snow.
If you love me and are kind,
Let us go home together.
Slowly, slowly! —
The time is urgent, oh!

Nothing red that is not a fox,
Nothing black that is not a crow.
If you love me and are kind,
Let us ride in one carriage.
Slowly, slowly! —
The time is urgent, oh!""",

    40: """The quiet girl is fair,
Waiting for me at the corner of the wall.
I love her, but cannot see her —
I scratch my head, I hesitate.

The quiet girl is lovely,
She gives me a red tube.
The red tube has its glow —
I delight in your beauty.

From the pasture she brings me the shoots,
Truly beautiful and strange.
It is not that you are beautiful —
It is the gift of my lady.""",

    41: """The new tower stands so bright,
The river waters murmur.
A mate of gentle grace I sought —
This fish-mouth is not what I wished.

The new tower stands so tall,
The river waters ripple.
A mate of gentle grace I sought —
This fish-mouth I cannot bear.

The net is set for fish,
But the goose is caught in it.
A mate of gentle grace I sought —
And got this hunchback instead.""",

    # ===== Chapter 4: 鄘风 =====
    42: """The wall has its thorns;
They cannot be swept away.
The words spoken within
Cannot be told.
What can be told —
The shame of such words!

The wall has its thorns;
They cannot be cleared away.
The words spoken within
Cannot be told in full.
What can be told in full —
The endlessness of such words!

The wall has its thorns;
They cannot be bound away.
The words spoken within
Cannot be spoken.
What can be spoken —
The disgrace of such words!""",

    44: """Where do we gather the dodder?
In the lands of Mei.
Whom do I think of?
The eldest of the Jiang.
She bade me wait in the mulberry grove,
She met me in the upper hall,
She saw me off by the banks of the Qi.

Where do we gather the wheat?
In the north of Mei.
Whom do I think of?
The eldest of the Yi.
She bade me wait in the mulberry grove,
She met me in the upper hall,
She saw me off by the banks of the Qi.

Where do we gather the turnip?
In the east of Mei.
Whom do I think of?
The eldest of the Yong.
She bade me wait in the mulberry grove,
She met me in the upper hall,
She saw me off by the banks of the Qi.""",

    46: """The rainbow is in the east —
None dares to point at it.
A girl goes forth to be wed,
Leaving father and mother, brother and sister.

The morning clouds rise in the west —
Before the morning is o'er, it rains.
A girl goes forth to be wed,
Leaving brother and sister, father and mother.

But this is a woman!
Who longs for marriage!
She has no faith at all,
And knows not her destiny.""",

    47: """Look at the rat — it has its skin;
A man without demeanour!
A man without demeanour —
What does he live for but to die?

Look at the rat — it has its teeth;
A man without restraint!
A man without restraint —
What does he wait for but to die?

Look at the rat — it has its body;
A man without propriety!
A man without propriety —
Why does he not quickly die?""",

    48: """The streaming yak-tail banner,
In the outskirts of Xun,
Adorned with white silk,
And four good horses.
That lovely gentleman —
What shall I give him?

The streaming falcon banner,
In the towns of Xun,
Plaited with white silk,
And five good horses.
That lovely gentleman —
What shall I offer him?

The streaming feather banner,
In the city of Xun,
Bound with white silk,
And six good horses.
That lovely gentleman —
What shall I say to him?""",

    49: """Driving fast, I hasten on,
To console the marquis of Wei.
I urge my horses, long the road,
Until I come to Cao.
The great officers toil and plod —
My heart is full of care.

You do not approve my course;
I cannot turn back.
I see you do not do well —
My thoughts go far.

You do not approve my course;
I cannot return across the stream.
I see you do not do well —
My thoughts are not stopped.

I climb that hill of Ao,
And gather the mallow.
A woman's heart is prone to grief,
But she too has her way.
The men of Xu blame her —
Foolish and wild they are!

I walk through the open fields,
Lush grows the wheat.
I would appeal to the great states —
Who will help, who will speed?
You great officers, you gentlemen,
Find no fault in me.
A hundred plans you make —
Not one matches what I would do.""",

    # ===== Chapter 5: 卫风 =====
    50: """Look at those bends of the Qi,
The green bamboo, fresh and dense!
There is our noble lord —
As if cut, as if filed;
As if chiselled, as if ground.
How stately! How dignified!
How majestic! How distinguished!
Our noble lord —
Never to be forgotten!

Look at those bends of the Qi,
The green bamboo, fresh and green!
There is our noble lord —
His ear-plugs of precious stone,
The gems upon his cap like stars.
How stately! How dignified!
How majestic! How distinguished!
Our noble lord —
Never to be forgotten!

Look at those bends of the Qi,
The green bamboo like a mat!
There is our noble lord —
Like gold, like tin;
Like a sceptre, like a gem.
How generous! How graceful!
Leaning on the carriage side!
How pleasant in his jesting!
Yet never harsh!""",

    51: """Make a hut in the ravine —
Great is the man's heart.
Alone he sleeps, he wakes, he speaks —
Forever vowing never to forget.

Make a hut on the slope —
Great is the man's content.
Alone he sleeps, he wakes, he sings —
Forever vowing never to depart.

Make a hut on the height —
Great is the man's delight.
Alone he sleeps, he wakes, he rests —
Forever vowing never to tell.""",

    52: """Tall is the lady and graceful,
A robe of silk over her brocade.
The daughter of the marquis of Qi,
The wife of the marquis of Wei,
Sister to the heir of the East Palace,
Sister to the marquis of Xing,
Sister-in-law to the lord of Tan.

Her fingers like the shoots of reed,
Her skin like congealed fat,
Her neck like the tree-grub,
Her teeth like melon seeds,
Her cicada head, her moth-antenna brows.
Ah, the dimples of her artful smile!
Ah, the beauty of her glancing eyes!

Tall is the lady and stately;
She halts by the fields and suburbs.
Four stallions, strong and proud,
Red-covered bridles, bright and fine.
In her pheasant-screened carriage she comes to court.
Great officers, retire betimes —
Give the lord no labour.

The river waters, broad and grand,
Flow northward, gurgling.
Cast the net — swish, swish;
Sturgeon and swordfish leap and flash.
Reeds and bulrushes rise high;
The ladies of the Jiang house, tall and fair;
The gentlemen, stalwart and bold.""",

    54: """Long and slim, the bamboo rod —
I fish in the Qi.
Do I not long for you?
But you are far, I cannot reach you.

The spring is on the left,
The Qi is on the right.
A girl, when she goes abroad,
Leaves brother and sister, father and mother.

The Qi is on the right,
The spring is on the left.
The beauty of her skilful smile,
The grace of her pendant gems.

The Qi flows gently by,
Cypress oars and cedar boat.
I harness my horse and ride abroad,
To ease my heart of sorrow.""",

    55: """My lord is brave and bold,
The hero of the land!
My lord holds the long lance,
The vanguard for the king.

Since my lord went to the east,
My hair is like flying tangle.
Have I no oils, no wash?
For whom should I adorn myself?

It rains! It rains!
But the sun comes out, so bright.
I long, I think of my lord —
My heart is willing to ache for it.

Where can I find the forget-grief grass?
I'll plant it by the northern wall.
I long, I think of my lord —
It makes my heart sick.""",

    56: """The fox moves slowly,
On the dam of the Qi.
The sorrow of my heart —
That man has no lower garment.

The fox moves slowly,
At the ford of the Qi.
The sorrow of my heart —
That man has no girdle.

The fox moves slowly,
By the bank of the Qi.
The sorrow of my heart —
That man has no clothes.""",

    57: """You threw me a quince —
I give you a precious gem.
Not as a return,
But to pledge our lasting love.

You threw me a peach —
I give you a precious jasper.
Not as a return,
But to pledge our lasting love.

You threw me a plum —
I give you a precious black jewel.
Not as a return,
But to pledge our lasting love.""",

    # ===== Chapter 6: 王风 =====
    59: """The rippling waters
Cannot float a faggot of wood.
That man there
Will not garrison Shen with me.
I long! Oh, I long!
What month shall I return?

The rippling waters
Cannot float a faggot of brambles.
That man there
Will not garrison Fu with me.
I long! Oh, I long!
What month shall I return?

The rippling waters
Cannot float a faggot of reeds.
That man there
Will not garrison Xu with me.
I long! Oh, I long!
What month shall I return?""",

    60: """In the valley grows the motherwort,
Parched and dried.
A wife is cast away;
She heaves a bitter sigh.
She heaves a bitter sigh!
To meet a man brings hardship!

In the valley grows the motherwort,
Parched and withered.
A wife is cast away;
She gives a long, deep wail.
She gives a long, deep wail!
To meet a man brings sorrow!

In the valley grows the motherwort,
Parched though it be wet.
A wife is cast away;
She sobs and weeps.
She sobs and weeps!
What lament can bring redress!""",

    61: """The hare moves free and easy,
But the pheasant is caught in the net.
In the days when I was born,
All was still and peaceful.
Now that I have grown,
I meet these hundred miseries.
Would I were asleep, with no more to stir!

The hare moves free and easy,
But the pheasant is caught in the snare.
In the days when I was born,
All was still and untroubled.
Now that I have grown,
I meet these hundred griefs.
Would I were asleep, never to wake!

The hare moves free and easy,
But the pheasant is caught in the trap.
In the days when I was born,
All was still and at rest.
Now that I have grown,
I meet these hundred terrors.
Would I were asleep, deaf to all!""",

    62: """Spread, spread the arrowroot vines,
On the bank of the river.
Far am I from brother and kin,
Calling another man 'father.'
Calling another man 'father' —
Yet he does not look on me.

Spread, spread the arrowroot vines,
On the edge of the river.
Far am I from brother and kin,
Calling another man 'mother.'
Calling another man 'mother' —
Yet she does not own me.

Spread, spread the arrowroot vines,
By the marge of the river.
Far am I from brother and kin,
Calling another man 'elder brother.'
Calling another man 'elder brother' —
Yet he does not hear me.""",

    63: """One who gathers the hemp —
A day without seeing her
Is like three months.

One who gathers the mugwort —
A day without seeing her
Is like three seasons.

One who gathers the artemisia —
A day without seeing her
Is like three years.""",

    65: """On the hill is the hemp,
There is Liu Zi-jie.
There is Liu Zi-jie —
He will come, slowly walking.

On the hill is the wheat,
There is Liu Zi-guo.
There is Liu Zi-guo —
He will come to eat.

On the hill is the plum,
There is that son of Liu.
There is that son of Liu —
He gives me a black jewel to wear.""",

    # ===== Chapter 7: 郑风 =====
    66: """How well the black robe fits!
When it is worn out,
I will make another.
I go to your chamber,
And on my return,
I give you fine attire.

How good the black robe is!
When it is worn out,
I will make anew.
I go to your chamber,
And on my return,
I give you fine attire.

How comfortable the black robe is!
When it is worn out,
I will make it over.
I go to your chamber,
And on my return,
I give you fine attire.""",

    67: """I pray you, Zhong-zi!
Do not leap into our hamlet,
Do not break our willow trees.
Do I dare grudge them?
I fear my father and mother.
Zhong is worthy to be loved —
But the words of father and mother
Are also to be feared.

I pray you, Zhong-zi!
Do not leap over our wall,
Do not break our mulberry trees.
Do I dare grudge them?
I fear my elder brothers.
Zhong is worthy to be loved —
But the words of my brothers
Are also to be feared.

I pray you, Zhong-zi!
Do not leap into our garden,
Do not break our sandalwood trees.
Do I dare grudge them?
I fear people will talk.
Zhong is worthy to be loved —
But the talk of people
Is also to be feared.""",

    68: """When Shu goes to the hunt,
The lane has no dwellers.
Are there no dwellers?
None like Shu —
Truly handsome and good.

When Shu goes a-hunting,
The lane has no revellers.
Are there no revellers?
None like Shu —
Truly handsome and fine.

When Shu goes to the wild,
The lane has no horsemen.
Are there no horsemen?
None like Shu —
Truly handsome and brave.""",

    69: """Shu goes to the hunt,
Riding four strong bays.
He holds the reins like ribbons,
The outrancers move like dancers.
Shu is in the marsh;
The torches all blaze up.
Baring his arm, he attacks the tiger,
And lays it before the duke.
Take care, Shu, do not try it again —
Beware lest it wound you!

Shu goes to the hunt,
Riding four yellow steeds.
The two leaders onward press,
The outrancers in goose-step.
Shu is in the marsh;
The torches all flame up.
Shu is skilled at shooting, ah!
And a good charioteer, ah!
Now he reins the gallop, ah!
Now he lets the arrow fly, ah!

Shu goes to the hunt,
Riding four dappled steeds.
The two leaders, head to head,
The outrancers like hands.
Shu is in the marsh;
The torches pile high.
Shu's horse goes slowly, ah!
His arrows fly seldom, ah!
He puts away the covered quiver, ah!
He lays aside the bow in its case, ah!""",

    70: """The men of Qing are at Peng,
Mail-clad horses, stamping.
Twin spears with double tassels —
Up and down by the river they ride.

The men of Qing are at Xiao,
Mail-clad horses, gleaming.
Twin spears with double rings —
Free and easy by the river they ride.

The men of Qing are at Zhou,
Mail-clad horses, steady.
Wheeling left and drawing right —
The centre ranks make a fine show.""",

    71: """The lamb's-fur robe, sleek and moist,
Truly upright and noble.
That man there —
Gives his life and changes not.

The lamb's-fur robe with leopard cuffs,
Truly strong and powerful.
That man there —
The straightener of the land.

The lamb's-fur robe, so fine!
Three ornaments, so bright!
That man there —
The glory of the land.""",

    72: """The wife says: 'The cock has crowed.'
The husband says: 'It is barely dawn.'
'Get up and look at the night;
The morning star is shining.
You should be off, you should be away,
To shoot the duck and goose.'

'You shoot and bring them down,
And I will dress them for you.
With the dressing, we'll drink wine,
And grow old together with you.
Lute and zither in attendance,
All is quiet and well.

Knowing you are coming,
I give you varied gems.
Knowing you are gentle,
I give you varied gems to ask.
Knowing you are loving,
I give you varied gems to repay.'""",

    73: """There is a lady in my carriage,
Her face like the blossoms of the hibiscus.
We drive, we fly —
Her pendant gems of jasper.
The eldest of the Jiang —
Truly lovely and elegant.

There is a lady walking with me,
Her face like the blossoms of the mallow.
We drive, we fly —
Her pendant gems go clang-clang.
The eldest of the Jiang —
Her virtuous name is not forgotten.""",

    74: """How splendid you are!
You waited for me in the lane —
Would that I had gone with you!

How grand you are!
You waited for me in the hall —
Would that I had escorted you!

I put on my silken robe,
My silken lower robe.
Uncles, elder brothers —
Harness the horses, I go with him.

My silken lower robe,
My silken robe.
Uncles, elder brothers —
Harness the horses, I go home.""",

    75: """Cold and bleak the wind and rain,
The cock crows, jie-jie.
Now that I see my lord,
How could my heart not be at peace?

Soughing, soughing, the wind and rain,
The cock crows, jiao-jiao.
Now that I see my lord,
How could my heart not be healed?

Dark as night the wind and rain,
The cock crows, on and on.
Now that I see my lord,
How could my heart not rejoice?""",

    76: """Blue, blue is your collar,
Long, long is my longing.
Though I do not go to you,
Why do you not send word?

Blue, blue is your pendant,
Long, long is my thought.
Though I do not go to you,
Why do you not come?

Lightly tripping, up and down,
On the gate-tower of the wall.
A day without seeing you
Is like three months.""",

    # ===== Chapter 8: 齐风 =====
    77: """'The cock has crowed!'
'The court is full!'
'It is not the cock that crows —
It is the sound of the bluebottle fly.'

'The east is bright!'
'The court is thronged!'
'It is not the east that is bright —
It is the light of the moon.'

'The insects hum and swarm —
I would gladly dream with you.
But the council will rise and go —
Let no one憎 us!'""",

    78: """How nimble you are!
You met me in the hunting-ground.
We raced together after two boars —
You bowed and called me skilled.

How fine you are!
You met me on the hunting-path.
We raced together after two stags —
You bowed and called me good.

How brave you are!
You met me on the south of the hunting-ground.
We raced together after two wolves —
You bowed and called me excellent.""",

    79: """You wait for me at the gate-screen,
Your ear-plugs of white.
Surmounted by a precious flower.

You wait for me in the courtyard,
Your ear-plugs of green.
Surmounted by a precious gem.

You wait for me in the hall,
Your ear-plugs of yellow.
Surmounted by a precious bloom.""",

    80: """Before the east is bright,
I put on robes wrong side out.
Wrong side out — and right again —
Called by a summons from the lord.

Before the east has shown its light,
I put on garments upside down.
Right side out — and wrong again —
Called by a command from the lord.

Break willow-branches to fence the garden —
The surly watchman stares.
I cannot tell the time of night —
If not too early, then too late.""",

    81: """High rises the southern hill,
The male fox moves slowly.
The road to Lu is broad and easy —
The lady of Qi went home by it.
Since she has gone home,
Why do you still long for her?

Straw sandals must be paired,
Hat-cords must be doubled.
The road to Lu is broad and easy —
The lady of Qi journeyed by it.
Since she journeyed,
Why do you still pursue her?

How do you plant the hemp?
You plough the furrows lengthwise and across.
How do you take a wife?
You must tell father and mother.
Since you have told them,
Why do you still persist?

How do you split the firewood?
Without an axe you cannot.
How do you take a wife?
Without a go-between you cannot.
Since you have obtained her,
Why do you still carry it to extremes?""",

    83: """The hound goes ling-ling,
Its master is fair and good.

The hound wears twin rings,
Its master is fair and curled.

The hound wears a chain,
Its master is fair and wise.""",

    84: """The broken basket is on the dam,
The fish — bream and tench.
The lady of Qi returns,
Her retinue like a cloud.

The broken basket is on the dam,
The fish — bream and carp.
The lady of Qi returns,
Her retinue like rain.

The broken basket is on the dam,
The fish slip to and fro.
The lady of Qi returns,
Her retinue like water.""",

    85: """The carriage rumbles along,
Bamboo screen and red hide.
The road to Lu is broad and easy —
The lady of Qi sets out at evening.

Four black horses, sleek and grand,
The hanging reins drip and drip.
The road to Lu is broad and easy —
The lady of Qi is glad of heart.

The Wen waters, broad and deep,
The wayfarers, thick and thronging.
The road to Lu is broad and easy —
The lady of Qi soars and sweeps.

The Wen waters, full and flowing,
The wayfarers, a countless crowd.
The road to Lu is broad and easy —
The lady of Qi wanders and roams.""",

    86: """Ah, how splendid!
Tall and graceful.
How stately his bearing!
His fine eyes, how they gleam!
How swift his dancing step!
And his archery — how skilled!

Ah, how renowned!
His fine eyes, how clear!
His ceremony complete,
All day long he shoots at the target —
Never missing the centre!
Truly my sister's son!

Ah, how lovely!
His clear brow, how gentle!
In the dance he keeps his place,
In his shooting he pierces through.
His four arrows return to the same spot —
A man to withstand disorder!""",

    # ===== Chapter 9: 魏风 =====
    87: """By the marshes of the Fen,
I gather the goosefoot.
That man there —
Beautiful beyond measure.
Beautiful beyond measure —
How different from the duke's road!

By the bank of the Fen,
I gather the mulberry leaves.
That man there —
Beautiful as a flower.
Beautiful as a flower —
How different from the duke's escort!

In a bend of the Fen,
I gather the water-purslane.
That man there —
Beautiful as jade.
Beautiful as jade —
How different from the duke's kin!""",

    88: """I climb that woody hill,
And gaze toward my father.
My father says: 'Alas, my son!
You serve, early and late, without rest.
Take care, oh take care!
Come back — do not stay there!'

I climb that barren hill,
And gaze toward my mother.
My mother says: 'Alas, my youngest!
You serve, early and late, without sleep.
Take care, oh take care!
Come back — do not forsake us!'

I climb that ridge,
And gaze toward my brother.
My brother says: 'Alas, my brother!
You serve, early and late, ever with others.
Take care, oh take care!
Come back — do not die there!'""",

    89: """Kan-kan we fell the sandalwood,
And lay it on the river's bank.
The river waters are clear and ripple.
You neither sow nor reap —
Why do you take three hundred sheaves of grain?
You neither hunt nor chase —
Why does your courtyard show dead badgers?
That noble man —
He does not eat idle bread!

Kan-kan we shape the wheel-spokes,
And lay them by the river's side.
The river waters are clear and straight.
You neither sow nor reap —
Why do you take three hundred stacks of grain?
You neither hunt nor chase —
Why does your courtyard show the great beast?
That noble man —
He does not eat idle food!

Kan-kan we make the wheel,
And lay it by the river's marge.
The river waters are clear and eddying.
You neither sow nor reap —
Why do you take three hundred bins of grain?
You neither hunt nor chase —
Why does your courtyard show the quail?
That noble man —
He does not eat idle fare!""",

    90: """Large rat, large rat!
Eat no more of our millet!
Three years we have fed you,
Yet you will not care for us.
We will leave you,
And go to that happy land.
Happy land, happy land —
There we shall find our place!

Large rat, large rat!
Eat no more of our wheat!
Three years we have fed you,
Yet you show us no gratitude.
We will leave you,
And go to that happy state.
Happy state, happy state —
There we shall find our due!

Large rat, large rat!
Eat no more of our young shoots!
Three years we have fed you,
Yet you give us no ease.
We will leave you,
And go to that happy suburbs.
Happy suburbs, happy suburbs —
Who there will ever weep?""",

    # ===== Chapter 10: 唐风 =====
    91: """The cricket is in the hall,
The year is drawing to its close.
If now we do not rejoice,
The days and months pass away.
But do not overdo your mirth —
Think on your station.
Love pleasure, but waste not —
The good man is full of care.

The cricket is in the hall,
The year is slipping by.
If now we do not rejoice,
The days and months hasten away.
But do not overdo your mirth —
Think on what lies beyond.
Love pleasure, but waste not —
The good man is ever alert.

The cricket is in the hall,
The service-carts are at rest.
If now we do not rejoice,
The days and months flow on.
But do not overdo your mirth —
Think on your cares.
Love pleasure, but waste not —
The good man is calm and content.""",

    92: """On the hills are the cork-trees,
In the low grounds the elms.
You have robes and garments,
But you trail them not, you wear them not.
You have carriages and horses,
But you drive them not, you gallop them not.
When you are dead and gone,
Another man will enjoy them.

On the hills are the ailanthus,
In the low grounds the mulberry.
You have courts and chambers,
But you sweep them not, you clean them not.
You have bells and drums,
But you beat them not, you strike them not.
When you are dead and gone,
Another man will keep them.

On the hills are the varnish-trees,
In the low grounds the chestnuts.
You have wine and food —
Why not daily thrum the lute?
With this be joyful, be glad,
And so prolong the day.
When you are dead and gone,
Another man will enter your chamber.""",

    93: """The rippling waters —
The white stones stand clear.
White robe with a red collar,
I follow you to Wo.
Now that I see my lord,
What cause for sorrow?

The rippling waters —
The white stones gleam bright.
White robe with red embroidery,
I follow you to Gu.
Now that I see my lord,
What cause for care?

The rippling waters —
The white stones glimmer.
I have heard of a command —
I dare not tell it to anyone!""",

    94: """Bind the faggot close;
The three stars are in the sky.
What night is this night?
I see this good man!
Ah, you! Ah, you!
What shall I do with this good man?

Bind the hay close;
The three stars are at the corner.
What night is this night?
I see this happy chance!
Ah, you! Ah, you!
What shall I do with this happy chance?

Bind the brambles close;
The three stars are at the door.
What night is this night?
I see this lovely one!
Ah, you! Ah, you!
What shall I do with this lovely one?""",

    97: """Gather the licorice, gather the licorice,
On the peak of Shou-yang.
The words that people say —
Do not believe them lightly.
Let them go, let them go!
Do not assent to them lightly.
The words that people say —
What do they gain?

Gather the sow-thistle, gather the sow-thistle,
At the foot of Shou-yang.
The words that people say —
Do not heed them lightly.
Let them go, let them go!
Do not assent to them lightly.
The words that people say —
What do they gain?

Gather the turnip, gather the turnip,
On the east of Shou-yang.
The words that people say —
Do not follow them lightly.
Let them go, let them go!
Do not assent to them lightly.
The words that people say —
What do they gain?""",

    # ===== Chapter 11: 秦风 =====
    98: """The carriages rumble by,
The horses with white-starred foreheads.
Before I saw my lord,
The chamberlain gave command.

On the slope is the varnish-tree,
In the low ground the chestnut.
Now that I see my lord,
We sit together and play the lute.
If today we do not rejoice,
The days that pass will see us old.

On the slope is the mulberry,
In the low ground the willow.
Now that I see my lord,
We sit together and play the reed-organ.
If today we do not rejoice,
The days that pass will see us gone.""",

    99: """Four iron-black horses, strong and high,
Six reins are in the hand.
The duke's favourite
Follows the duke to the hunt.

They offer the seasonal stag,
The seasonal stag is large and fine.
The duke says: 'To the left!'
They loose the shaft, and the beast is won.

They roam in the north park,
The four horses are well trained.
The light car with tinkling bits
Carries hounds that rest from their quest.""",

    100: """The light war-car, small behind,
With five bindings on the curved pole,
With running rings and side-reins,
With yoke-bands and white-metal clasps,
With figured mat and long hub —
I drive my piebald with white socks.
I think of my lord,
Gentle as jade.
In his plank-walled tent,
He stirs my heart to tumult.

Four stallions, strong and grand,
Six reins held in the hand,
Bay and roan in the middle,
Grey and black on the outside.
Dragon shields close together,
Joined with white-metal rings.
I think of my lord,
Gentle, in the town.
When will the time come round?
Why do I yearn for him so?

The light war-team moves well,
The three-edged spear with white-metal socket,
The shield with figured face,
The tiger-skin bow-case with chased front,
Two bows in crossed cases,
Bamboo clamps and bound string.
I think of my lord,
Now sleeping, now waking.
So gentle is my lord,
Of ordered and virtuous fame.""",

    101: """Dense, dense are the reeds and rushes,
White dew turned to frost.
The one I speak of
Is on the other side of the water.
Upstream I seek — the way is hard and long.
Downstream I seek — and lo, there in the midst of the water!

Dense, dense are the reeds and rushes,
White dew not yet dry.
The one I speak of
Is on the margin of the water.
Upstream I seek — the way is steep and high.
Downstream I seek — and lo, there on the islet of the water!

Dense, dense are the reeds and rushes,
White dew not yet spent.
The one I speak of
Is on the bank of the water.
Upstream I seek — the way winds and turns.
Downstream I seek — and lo, there on the sandbar of the water!""",

    103: """How swift the morning hawk,
How dense the northern grove!
I have not seen my lord,
My heart is full of anxious care.
What is to be done? What is to be done?
He has indeed forgotten me much.

On the hills are the clustered oaks,
In the low grounds the six-trunked trees.
I have not seen my lord,
My heart finds no delight.
What is to be done? What is to be done?
He has indeed forgotten me much.

On the hills are the clustered cherries,
In the low grounds the pear-trees.
I have not seen my lord,
My heart is as if drunken.
What is to be done? What is to be done?
He has indeed forgotten me much.""",

    # ===== Chapters 12-30: remaining odes (104-252) =====
    104: """Who says you have no clothes?
I will share my long robe with you.
The king is raising hosts —
I will mend my spear and lance,
And share your foe with you.

Who says you have no clothes?
I will share my undergarment with you.
The king is raising hosts —
I will mend my halberd and spear,
And rise together with you.

Who says you have no clothes?
I will share my lower robe with you.
The king is raising hosts —
I will mend my armour and arms,
And march together with you.""",

    105: """How you sway and dance,
On the top of Wan Hill!
Truly you have feeling —
But there is no hope.
Thud-thud sounds the drum,
At the foot of Wan Hill.
Through winter and summer,
You wave the egret's feather.
Thud-thud sounds the earthen drum,
On the road of Wan Hill.
Through winter and summer,
You wave the egret's plume.""",

    106: """The elm at the eastern gate,
The oak on Wan Hill.
The son of Zi-zhong
Dances beneath them.

We choose an auspicious morning,
On the plain of the south.
She spins not her hemp,
But dances in the market-place.

We pass an auspicious morning,
And the crowd moves on together.
I look at you as at the mallow-flower —
You give me a handful of pepper.""",

    107: """Beneath the balancing gate,
One may rest and linger.
By the pellucid waters of Bi,
One may satisfy hunger.

If we would eat fish,
Must it be the bream of the river?
If we would take a wife,
Must she be a Jiang of Qi?

If we would eat fish,
Must it be the carp of the river?
If we would take a wife,
Must she be a Zi of Song?""",

    108: """In the pools by the eastern gate,
One may ret the hemp.
That lovely lady of the Ji —
One may sing with her.

In the pools by the eastern gate,
One may ret the china-grass.
That lovely lady of the Ji —
One may converse with her.

In the pools by the eastern gate,
One may ret the sedge.
That lovely lady of the Ji —
One may talk with her.""",

    109: """The moon comes forth in her brightness,
How lovely is the lady!
Slowly she moves in her elegance,
My sorrowing heart is stirred.

The moon comes forth in her whiteness,
How charming is the lady!
Slowly she moves in her grace,
My sorrowing heart is troubled.

The moon comes forth and shines,
How radiant is the lady!
Slowly she moves in her beauty,
My sorrowing heart is wrung.""",

    110: """On the banks of that marsh,
Grow the rushes and the lotus.
There is a beautiful lady —
I yearn — what shall I do?
Waking and sleeping I know no peace,
My tears fall in streams.

On the banks of that marsh,
Grow the rushes and the lotus-leaves.
There is a beautiful lady,
Tall and graceful.
Waking and sleeping I know no peace,
My heart is full of grief.

On the banks of that marsh,
Grow the rushes and the lotus-blooms.
There is a beautiful lady,
Tall and stately.
Waking and sleeping I know no peace,
I toss and turn upon my pillow.""",

    111: """In lamb's-fur robe he saunters,
In fox-fur robe he goes to court.
How can I not long for him?
My anxious heart is torn.

In lamb's-fur robe he roams,
In fox-fur robe he is in the hall.
How can I not long for him?
My heart is full of grief.

The lamb's-fur robe is glossy as oil,
The rising sun makes it shine.
How can I not long for him?
My heart within is grieved.""",

    112: """I see the white cap!
The wasted man, so thin!
My sorrowing heart throbs!

I see the white robe!
My heart is full of grief!
Let me return with you!

I see the white knee-covers!
My heart is bound with care!
Let me be one with you!""",

    113: """In the low grounds grows the chang-chu,
How graceful are its branches!
Fresh and glossy —
I envy you your want of feeling!

In the low grounds grows the chang-chu,
How graceful are its flowers!
Fresh and glossy —
I envy you your freedom from home!

In the low grounds grows the chang-chu,
How graceful is its fruit!
Fresh and glossy —
I envy you your freedom from household!""",

    114: """How whirls the wind!
How speeds the carriage!
I look back upon the great road,
And my heart is full of grief.

How blows the wind!
How the carriage hurries!
I look back upon the great road,
And my heart is sad.

Who can cook the fish?
Let him wash the pot.
Who is going west?
Let him carry kind words.""",

    115: """The wings of the ephemera,
Robes so smart and trim.
The sorrow of my heart —
Where shall I find a place?

The wings of the ephemera,
Garments so bright and gay.
The sorrow of my heart —
Where shall I find a rest?

The ephemera bursts from the ground,
Its linen garments white as snow.
The sorrow of my heart —
Where shall I find shelter?""",

    116: """That watchman at the gate —
He carries a spear and a club.
That man there —
Three hundred wear the red knee-covers!

The pelican is on the dam,
Its wings are not wet.
That man there —
His garments do not fit him!

The pelican is on the dam,
Its beak is not wet.
That man there —
He does not attain his match!

Luxuriant, luxuriant!
The morning clouds on the southern hill.
Soft and fair,
The youngest daughter — she is hungry!""",

    117: """The cuckoo is in the mulberry,
Its seven young ones.
The good and noble man —
His demeanour is ever one.
His demeanour is ever one —
His heart is bound fast.

The cuckoo is in the mulberry,
Its young ones in the plum.
The good and noble man —
His girdle is of silk.
His girdle is of silk —
His cap has a piebald ornament.

The cuckoo is in the mulberry,
Its young ones in the jujube.
The good and noble man —
His demeanour is without fault.
His demeanour is without fault —
He is the model of the four quarters of the state.

The cuckoo is in the mulberry,
Its young ones in the hazel.
The good and noble man —
He is the model of the people.
He is the model of the people —
How should he not live ten thousand years?""",

    118: """Cold is the gushing spring,
Watering the bushy grain.
I wake and sigh,
Thinking of the capital of Zhou.

Cold is the gushing spring,
Watering the bushy mugwort.
I wake and sigh,
Thinking of the capital of Zhou.

Cold is the gushing spring,
Watering the bushy yarrow.
I wake and sigh,
Thinking of the capital.

Lush grows the millet shoot,
The gentle rain nourishes it.
The states of the realm have their king —
The Earl of Xun comforts them.""",

    120: """O owl, O owl!
You have already taken my young ones —
Do not destroy my nest!
With love and labour I reared them —
In pity for my little ones.

Before the sky yet clouds over,
I tear off the mulberry bark,
And bind fast the windows and doors.
Now you people below —
Who dares to affront me?

My hands are sore and cramped;
I gather the sow-thistle leaves;
I heap up my stores;
My mouth is worn to the bone —
They say I have no house.

My feathers are thinned and torn,
My tail is ragged and rent.
My nest is tottering high —
Tossed by wind and rain.
I can only cry in fear.""",

    121: """I went to the eastern hills,
Long, long I stayed away.
I come from the east now,
In the falling, drizzling rain.
When in the east I said I would return,
My heart yearned to the west with grief.

I will make robes and garments,
And no more carry the word in my mouth.
The writhing caterpillar
Lies thick in the mulberry fields.
I huddle alone, a-rounded up —
Even under the chariot I sleep.

I went to the eastern hills...
The fruit of the gourd-vine
Hangs along the eaves.
Wood-lice crawl in the house,
Spiders weave at the door.
The deer tread the village paths,
The glow-worms flit at night.
It is not to be dreaded —
But it is a place to long for.

I went to the eastern hills...
The stork cries on the ant-hill;
The wife sighs in the house.
Sweep the rooms, fill the cracks —
My soldier is coming home.
The gourd is round and bitter,
Piled among the chestnut faggots.
Since we parted,
It is now three years.

I went to the eastern hills...
The golden oriole flies,
Its plumage glittering.
The lady went to her new home,
The horses bay and chestnut.
Her mother tied her sash,
With ninety ceremonials.
The new wife is very fair —
But what of the old?""",

    122: """My axe is broken,
And my adze is chipped.
The duke of Zhou marched east —
And the four quarters stood in awe.
Alas for us, the people!
How great our deliverance!

My axe is broken,
And my chisel is chipped.
The duke of Zhou marched east —
And the four quarters were reformed.
Alas for us, the people!
How good our deliverance!

My axe is broken,
And my mallet is chipped.
The duke of Zhou marched east —
And the four quarters were brought to order.
Alas for us, the people!
How blessed our deliverance!""",

    123: """The fish in the nine-meshed net —
The trout and the bream.
I see this man,
In his embroidered robes and figured skirt.

The wild goose flies along the islet —
The duke goes home to no fixed place.
With you I would stay awhile.

The wild goose flies along the shore —
The duke goes home, to return no more.
With you I would stay another night.

Therefore he has his embroidered robes —
Do not let my duke go away!
Do not make my heart sad!""",

    124: """Yōu-yōu cry the deer,
Nibbling the wild southernwood.
I have honoured guests —
We play the lute, we blow the organ.
We blow the organ, we strike the reeds,
We present the baskets of gift.
The people who love me —
They show me the right way.

Yōu-yōu cry the deer,
Nibbling the wild sage.
I have honoured guests —
Their virtuous fame is bright.
They show the people no frivolity —
The noble man takes them as his model.
I have sweet wine —
My honoured guests feast and rejoice.

Yōu-yōu cry the deer,
Nibbling the wild asparagus.
I have honoured guests —
We play the lute, we play the zither.
We play the lute, we play the zither —
In harmony and deepest joy.
I have sweet wine —
To feast and gladden the hearts of my honoured guests.""",

    125: """Four steeds untiring,
The great road winds and bends.
How can I not long to return?
The king's affairs press hard —
My heart is full of grief.

Four steeds untiring,
The white-maned horses pant.
How can I not long to return?
The king's affairs press hard —
I find no time to rest.

Flits the dove, flits it so,
Now on the wing, now dropping down,
Alighting on the clustering oak.
The king's affairs press hard —
I find no time to tend my father.

Flits the dove, flits it so,
Now on the wing, now at rest,
Alighting on the clustering tamarisk.
The king's affairs press hard —
I find no time to tend my mother.

I harness those four white-maned steeds,
They gallop, swift and fleet.
How can I not long to return?
Therefore I make this song —
To tell my mother of my longing.""",

    126: """Bright, bright are those flowers,
On those plains and low grounds.
Speed, speed the wayfarers,
Their hearts full of anxious thought.

My horses are young,
The six reins drip wet.
We drive fast, we haste —
We seek counsel everywhere.

My horses are piebald,
The six reins like silk.
We drive fast, we haste —
We seek counsel and plan everywhere.

My horses are white-maned,
The six reins glossy and bright.
We drive fast, we haste —
We seek counsel and consider everywhere.

My horses are grey,
The six reins all even.
We drive fast, we haste —
We seek counsel and inquire everywhere.""",

    127: """The blossoms of the cherry-apple,
Are they not gorgeous?
Of all the men of the present day,
None are like brothers.

In the terror of death and bereavement,
Brothers take thought of each other.
The plains and low grounds are heaped with the dead —
Brothers seek one another out.

The wagtail is on the moor —
Brothers hurry to the rescue.
Though there be good friends —
They can only heave a long sigh.

Brothers may quarrel within the walls —
But outside, they resist the foe.
Though there be good friends —
They will not come to the rescue.

Trouble and tumult are past,
Peace and quiet restored.
Though there be brothers —
They are not as friends.

Set out your dishes and cups,
Drink your fill at the feast.
The brothers are all assembled —
In harmony and family love.

Wife and children in happy union —
Like the lute and zither played together.
Brothers in concord —
In harmony and deepest joy.

Order your household well,
Rejoice in your wife and children.
Look into this, think on it —
Is it not truly so?""",

    130: """Gather the vetch, gather the vetch,
The vetch has sprung up.
We say we will return, we say we will return —
The year is drawing to its close.
No wife, no home —
Because of the Xian-yun.
We have no time to rest —
Because of the Xian-yun.

Gather the vetch, gather the vetch,
The vetch is soft and tender.
We say we will return —
My heart is full of grief.
My sorrow is fierce and burning,
I hunger, I thirst.
Our garrison is not yet fixed —
No one can be sent home with a message.

Gather the vetch, gather the vetch,
The vetch is hard and stiff.
We say we will return —
The year is in its tenth month.
The king's affairs press hard —
I find no time to rest.
My heart is full of bitter pain —
I came here, but none will come to me.

What is that in bloom?
It is the blossoms of the cherry-tree.
What is that on the road?
It is the carriage of our lord.
The war-cars are harnessed,
Four stallions, tall and strong.
How can we settle down?
In one month, three battles.

We harness those four stallions,
Four steeds, strong and grand.
The noble man leans upon them,
The footman follows behind.
Four steeds in steady order,
Bow-tips of horn and quivers of fish-skin.
How can we fail to be daily on guard?
The Xian-yun are very swift!

Long ago, when we set out,
The willows were fresh and green.
Now, when I return,
The rain and snow fall thick.
The road is long and slow,
I hunger, I thirst.
My heart is full of grief —
But none knows my sorrow!""",

    131: """I bring out my carriage,
On the pasture-land.
From the Son of Heaven's dwelling,
I am bidden to come.
I call the driver,
And bid him yoke the team.
The king's affairs are full of trouble —
And all is urgent.

I bring out my carriage,
In the open country.
We set up the serpent-banner,
We raise the yak-tail flag.
Those banners and those flags —
Why do they not stream?
My heart is full of secret care —
The driver is worn and spent.

The king commands Nan-zhong,
To build the wall at Fang.
The war-cars go rumbling out,
The banners glowing bright.
The Son of Heaven bids me
Build the wall in the north.
Illustrious Nan-zhong —
The Xian-yun are subdued.

Long ago, when we set out,
The millet was in bloom.
Now, when I return,
The rain and snow choke the road.
The king's affairs are full of trouble —
We find no time to rest.
How can we fail to long for home?
We fear the bonds of the bamboo-slip command.

Yōu-yōu cry the grasshoppers,
Chirp-chirp the locusts.
I have not seen my lord,
My heart is full of sorrow.
Now that I see my lord,
My heart is at rest.
Illustrious Nan-zhong —
He smites the western Rong.

The spring days draw long,
Trees and shrubs are lush.
The golden orioles cry, jie-jie,
They gather the white southernwood, in crowds.
We take the captives and the chieftains,
And make our way home.
Illustrious Nan-zhong —
The Xian-yun are destroyed.""",

    133: """The fish are in the weir —
The yellow-jaw and the shark.
The noble man has wine —
Delicious and abundant.

The fish are in the weir —
The bream and the snake-head.
The noble man has wine —
Abundant and delicious.

The fish are in the weir —
The tench and the carp.
The noble man has wine —
Delicious and plentiful.

The things are many —
And they are good.
The things are delicious —
And they are together.
The things are plentiful —
And they are in season.""",

    134: """In the south are fine fish —
They dart and dip beneath the nets.
The noble man has wine —
His honoured guests feast and rejoice.

In the south are fine fish —
They dart and dip in the trap.
The noble man has wine —
His honoured guests feast and are glad.

In the south are the drooping trees,
The sweet gourd twines about them.
The noble man has wine —
His honoured guests feast and are at peace.

Flits the dove, flits it so —
It comes in great numbers.
The noble man has wine —
His honoured guests feast and gather again.""",

    135: """On the southern hill is the spear-grass,
On the northern hill the goosefoot.
Joyful is the noble man —
The foundation of the state.
Joyful is the noble man —
May he live ten thousand years without end!

On the southern hill is the mulberry,
On the northern hill the willow.
Joyful is the noble man —
The glory of the state.
Joyful is the noble man —
May he live ten thousand years for ever!

On the southern hill is the medlar,
On the northern hill the plum.
Joyful is the noble man —
The father and mother of the people.
Joyful is the noble man —
May his virtuous fame never cease!

On the southern hill is the ailanthus,
On the northern hill the celtis.
Joyful is the noble man —
Why should he not live to hoary age?
Joyful is the noble man —
May his virtuous fame flourish!

On the southern hill is the grape-vine,
On the northern hill the birch.
Joyful is the noble man —
Why should he not live to a good old age?
Joyful is the noble man —
May he protect and bless his posterity!""",

    136: """Long are the mugwort leaves,
The falling dew is heavy.
Now that I see my lord,
My heart is at ease.
We feast and laugh and talk —
Therefore we have praise and rest.

Long are the mugwort leaves,
The falling dew is thick.
Now that I see my lord,
I am honoured and glorious.
His virtue is without flaw —
May he live to a good old age and not be forgotten!

Long are the mugwort leaves,
The falling dew is wet.
Now that I see my lord,
In great feasting, kind and glad.
Right for brother, right for brother —
In good virtue, long and happy!

Long are the mugwort leaves,
The falling dew is dense.
Now that I see my lord,
The bit-and-bridle ornaments tinkling.
The bells and the sounding-blocks harmonious —
All blessings are gathered here.""",

    137: """Heavy, heavy lies the dew,
It dries not till the sun comes forth.
Gently we drink the night away —
None returns till he is drunk.

Heavy, heavy lies the dew,
Among the luxuriant grass.
Gently we drink the night away —
In the ancestral temple we strike the time.

Heavy, heavy lies the dew,
Among the medlars and jujubes.
Illustrious and true, the noble men —
There is none without good virtue.

The tung-tree and the cherry-tree,
Their fruit hangs thick.
Kind and gentle, the noble men —
There is none without good bearing.""",

    138: """The red bow is unstrung —
We receive it and store it away.
I have honoured guests —
My heart rejoices in them.
Bells and drums are set —
One morning we feast them.

The red bow is unstrung —
We receive it and bear it away.
I have honoured guests —
My heart delights in them.
Bells and drums are set —
One morning we attend them.

The red bow is unstrung —
We receive it and put it in its case.
I have honoured guests —
My heart loves them.
Bells and drums are set —
One morning we pledge them.""",

    139: """Luxuriant grows the artemisia,
On the hill-slopes in the midst.
Now that I see my lord —
I am glad, and he shows his bearing.

Luxuriant grows the artemisia,
On the islet in the midst.
Now that I see my lord —
My heart is glad.

Luxuriant grows the artemisia,
On the ridge in the midst.
Now that I see my lord —
He gives me a hundred strings of cowries.

The poplar-boat drifts to and fro —
Now sinking, now floating.
Now that I see my lord —
My heart is at rest.""",

    140: """In the sixth month we toil,
The war-cars are made ready.
Four stallions, strong and grand,
We bear the dragon-banner of our post.
The Xian-yun are fiercely raging —
Therefore we haste.
The king bids us march —
To save the royal kingdom.

We match the teams of four black horses,
We train them to the rules.
In this sixth month,
Our gear is all complete.
Our gear complete,
We march thirty li a day.
The king bids us march —
To help the Son of Heaven.

Four steeds, long and large,
So tall and big.
We smite the Xian-yun —
To win great merit.
Reverent and careful —
We share the toil of war.
Sharing the toil of war —
We settle the royal kingdom.

The Xian-yun, undaunted,
Encamp at Jiao-hu.
They invade Hao and Fang,
Up to the north of the Jing.
Figured banners with the bird-device,
White streamers glowing bright.
Ten war-cars of the vanguard —
To open the way.

The war-cars move at ease,
Now low, now high.
The four steeds, well in hand —
Well in hand and well trained.
We smite the Xian-yun —
Up to the great plain.
The accomplished Ji-fu, civil and military —
A model to ten thousand states.

Ji-fu feasts and rejoices,
He has received many blessings.
Returning from Hao —
Our march has been long.
We feast our friends with wine,
Roast turtle and minced carp.
Who is there among them?
Zhang-zhong, filial and brotherly.""",

    141: """We gather the white millet,
In the new-ploughed fields,
On the year-old acres.
Fang-shu comes,
With three thousand chariots,
The host testing its shields.
Fang-shu leads them on,
Riding his four piebald steeds,
Four steeds in steady order.
State-carriage, glowing red,
Bamboo screen and fish-skin quiver,
Bitted yoke and tug of leather.

We gather the white millet,
In the new-ploughed fields,
In the midst of the country.
Fang-shu comes,
With three thousand chariots,
Banners and flags glowing bright.
Fang-shu leads them on,
With bound axle and painted pole,
Eight bells ringing clear.
In his appointed robes he serves,
The red knee-covers glowing,
The bluish-green gems ringing.

Swift flies the falcon,
It soars to the sky,
Yet it alights and rests.
Fang-shu comes,
With three thousand chariots,
The host testing its shields.
Fang-shu leads them on,
The gong-men strike the drums,
He marshals the host and rallies the ranks.
Illustrious and true Fang-shu —
He beats the drums, deep-rolling,
And leads back the host in triumph.

Ye wild men of Jing, so foolish!
You make a great state your foe.
Fang-shu, the elder statesman —
His plans are strong and bold.
Fang-shu leads them on —
He takes the captives and the chieftains.

The war-cars rumble on,
Rumble and roll,
Like thunder, like the storm.
Illustrious and true Fang-shu —
He marched against the Xian-yun,
And the men of Jing came in awe.""",

    142: """My carriage is repaired,
My horses all matched.
Four stallions, strong and grand —
We harness them and go to the east.

The hunting-cars are good,
Four steeds, tall and strong.
In the east are the grassy lands of Fu —
We harness and ride to the hunt.

The master goes a-field —
He selects his men, a noisy crowd.
He raises the banners, sets the flags,
And hunts the beasts at Ao.

We harness those four steeds,
Four steeds, sleek and shining.
In red knee-covers and gold-shoon —
The lords assemble in order.

The archer's rings and thimble are fitted,
Bow and arrows are well-adjusted.
The shooters are matched and ready —
They help to pile up the game.

Four yellows are harnessed,
The two outrancers do not swerve.
We keep the pace, we loose the shafts —
Like cleaving, it pierces.

The horses neigh, neigh,
The banners stream and flutter.
Foot and horse are not startled —
The great kitchen overflows.

The master marches home —
There is noise, but no disorder.
Truly a noble man —
He has achieved great things!""",

    143: """On the lucky day of Wu,
We sacrifice to the Father of the Hunt and pray.
The hunting-cars are good,
Four steeds, tall and strong.
We climb the great hill —
And follow the herds.

On the lucky day of Geng-wu,
We choose our horses well.
Where the beasts congregate —
The hinds and stags, in troops.
Down the Jin and the Ju they flee —
The Son of Heaven's hunting-ground.

We look upon the central plain —
It is full of great beasts.
Rushing, hurrying, or in herds, or in bands.
We drive them, right and left —
To feast the Son of Heaven.

I have bent my bow,
I have set my arrow to the string.
I loose at the little sow —
I lay low the great rhinoceros.
To entertain our guests —
And to pour out the sweet wine.""",

    144: """The wild geese fly,
Fluttering their wings.
The people are on the march,
Toiling in the open country.
We reach out to the destitute,
Pitying the widows and the bereaved.

The wild geese fly,
Settling in the midst of the marsh.
The people are on the wall-building,
A hundred walls go up.
Though we toil and travail —
In the end, there is a home to dwell in.

The wild geese fly,
Their mournful cry, āo-āo.
The wise man says we toil and travail.
The foolish man says we are proud and idle.""",

    145: """How goes the night?
The night is not yet half spent.
The torches in the courtyard blaze —
The noble men have come,
The bells of the carriage ring clear.

How goes the night?
The night is not yet over.
The torches in the courtyard flicker —
The noble men have come,
The bells of the carriage trill.

How goes the night?
The night gives way to morning.
The torches in the courtyard smoke —
The noble men have come,
We watch their banners appear.""",

    146: """The flowing waters,
Like courtiers, hasten to the sea.
Swift flies the falcon,
Now on the wing, now at rest.
Alas, my brothers!
People of the state, my friends!
None will think of the turmoil —
Who has not father and mother?

The flowing waters,
Their current broad and deep.
Swift flies the falcon,
Now on the wing, now soaring.
I think of those who walk not in the right way —
I rise, I pace the floor.
The sorrow of my heart —
I cannot banish, I cannot forget.

Swift flies the falcon,
Following the ridges of the hill.
The slanderous talk of the people —
Why is it not punished?
My friends, be on your guard —
Slanderous words will rise!""",

    147: """The crane cries in the deep marsh —
Its voice is heard in the wild.
Fish lie deep in the abyss,
Or sport among the islets.
In that pleasant garden —
There stands the sandal-tree,
Beneath it, the fallen leaves.
The stones of other hills —
May serve to polish gems.

The crane cries in the deep marsh —
Its voice reaches to heaven.
Fish sport among the islets,
Or lie deep in the abyss.
In that pleasant garden —
There stands the sandal-tree,
Beneath it, the brushwood.
The stones of other hills —
May serve to polish gems.""",

    148: """O Father of the War!
I am the fang and claw of the king.
Why do you cast me into distress?
I have no place to dwell.

O Father of the War!
I am the guardsman of the king.
Why do you cast me into distress?
I have no place to rest.

O Father of the War!
Truly you are not wise.
Why do you cast me into distress?
I have a mother — but who prepares her meal?""",

    149: """The bright white colt
Eats the shoots of my garden.
I tether it, I halter it —
To prolong this morning.
The one I speak of —
Here he lingers at ease.

The bright white colt
Eats the bean-leaves of my garden.
I tether it, I halter it —
To prolong this evening.
The one I speak of —
Here he is a welcome guest.

The bright white colt —
It comes, so brightly.
Be you duke, be you marquis —
Enjoy yourself without end.
Take heed in your wanderings —
Restrain your thoughts of flight.

The bright white colt —
There in the empty valley,
A bundle of fresh grass.
Its rider is like jade —
Prize not your voice as gold and jade,
And form a heart estranged!""",

    151: """I walk through the wild,
The foul-tree's leaves are thick.
For the sake of our marriage —
I came to dwell with you.
You cherish me no longer —
I return to my own home.

I walk through the wild,
I gather the parsley.
For the sake of our marriage —
I came to lodge with you.
You cherish me no longer —
I return to my own place.

I walk through the wild,
I gather the convolvulus.
You think not of our old bond,
You seek some new match.
It is not that they are richer —
It is only that you are changed.""",

    162: """Who is that man?
His heart is very hard.
Why does he pass my dam,
And not enter my gate?
Who is he with?
Only with the violent.

Two men walk together —
Who caused this calamity?
Why does he pass my dam,
And not come to console me?
At first it was not so —
Now he says I am not to his mind.

Who is that man?
Why does he pass my hall?
I hear his voice,
But do not see his form.
He feels no shame before men —
He fears not Heaven.

Who is that man?
He is like the whirlwind.
Why does he not go north?
Why does he not go south?
Why does he pass my dam?
He only troubles my heart.

When you go at your ease,
You find no time to halt.
When you go in haste —
You find time to grease your axle?
When you came to me once —
How my heart yearned!

You return and enter —
My heart is at peace.
You return and do not enter —
I cannot fathom you.
When you came to me once —
You made me glad.

The elder brother plays the ocarina,
The younger plays the flute.
You and I were strung as one —
Yet you say you do not know me.
Bring forth these three victims —
To swear an oath against you.

If you were a ghost or a water-demon,
You could not be found out.
But you have a face and eyes,
Looking on men without end.
I make this good song —
To lay bare your treachery.""",

    164: """Gently blows the east wind,
With wind and rain.
In fear and trembling —
I was with you.
Now in peace and joy —
You turn and cast me off.

Gently blows the east wind,
With wind and tempest.
In fear and trembling —
You held me to your heart.
Now in peace and joy —
You cast me off like a thing forgotten.

Gently blows the east wind,
On the high and rugged hill.
No grass but dies,
No tree but withers.
You forget my great virtues —
And remember my small faults.""",

    165: """Tall and tall grows the artemisia,
But it is not artemisia — it is the wild wormwood.
Alas, alas, my father and mother!
You bore me in toil and travail.

Tall and tall grows the artemisia,
But it is not artemisia — it is the wild purslane.
Alas, alas, my father and mother!
You bore me in weariness and pain.

The jar is empty —
It is the larger vessel's shame.
The orphaned one's life —
Were better ended long ago in death.
Without a father, on whom can I lean?
Without a mother, on whom can I rely?
When I go out, I bear my grief —
When I come in, I seem to have nowhere to go.

My father gave me life,
My mother nourished me.
They caressed me, they reared me,
They made me grow, they tended me,
They looked on me, they returned to me,
In going out and coming in, they bore me in their arms.
The kindness I would repay —
Is vast as boundless Heaven.

The southern hill is rugged and steep,
The whirlwind blows, blow on blow.
All the people nourish their parents —
Why am I alone afflicted?

The southern hill is high and grand,
The whirlwind blows, swift on swift.
All the people nourish their parents —
I alone am not suffered to fulfil my duty!""",

    167: """In the fourth month it is summer,
In the sixth month the heat comes on.
Are my ancestors not men?
Why do they thus suffer me to endure?

The autumn days are chill and drear,
All the plants are withering.
In the tumult of exile and woe —
Where shall I turn for rest?

The winter days are fierce and biting,
The whirlwind blows, blow on blow.
All the people enjoy good cheer —
Why am I alone afflicted?

On the hills are goodly plants —
Chestnuts and plums.
Ruined and made a curse —
And none knows the cause.

Look at the spring-waters —
Now clear, now muddy.
Day after day I meet with trouble —
How can I make things go well?

The Jiang and the Han, broad and rolling,
Are the arteries of the southern lands.
I have worn myself out in service —
And yet you will not own me.

If I were a hawk or a kite,
I would soar to the sky.
If I were a sturgeon or a wei-fish,
I would dive to the depths.

On the hills are ferns and vetches,
In the low grounds, medlars and birches.
The noble man makes this song —
Only to tell his sorrow.""",

    168: """I climb that northern hill,
And gather the medlars.
Strong and stalwart officers,
Morning and evening, serve.
The king's affairs are without end —
My father and mother are sad.

Under the wide heaven,
All is the king's land.
To the shores of the sea,
All are the king's subjects.
The great officers are not just —
I alone serve, more than all.

Four steeds, panting and grand,
The king's affairs crowd thick.
They praise me that I am not yet old,
They are glad that I am just in my prime.
My strength is at its height —
I am sent to toil in every corner.

Some live at ease in their homes,
Some wear themselves out for the state.
Some lie resting on their beds,
Some are ever on the march.

Some know not the cry of distress,
Some toil in grief and pain.
Some lounge and loiter at will,
Some are overwhelmed by the king's affairs.

Some feast and make merry with wine,
Some live in fear of blame.
Some gossip as they go in and out,
Some have no work they do not do.""",

    169: """Do not push the great cart —
You will only be covered with dust.
Do not harbour a hundred cares —
You will only make yourself ill.

Do not push the great cart —
The dust is dark and blinding.
Do not harbour a hundred cares —
You will never see your way clear.

Do not push the great cart —
The dust is thick and choking.
Do not harbour a hundred cares —
You will only burden yourself.""",

    171: """The bells go chang-chang,
The waters of the Huai go surging on.
My heart is full of grief.
The good and noble man —
I think of him and will not forget.

The bells go jie-jie,
The waters of the Huai go rippling on.
My heart is full of sorrow.
The good and noble man —
His virtue is without crookedness.

The bells beat the great drum,
On the three isles of the Huai.
My heart is full of grief.
The good and noble man —
His virtue is not at fault.

The bells go chin-chin,
We play the lute, we play the zither.
The organ and the sounding-blocks are in harmony.
With the Ya and the Nan they blend —
With the flute-reed, none is out of place.""",

    176: """Look at the waters of the Luo,
How broad and grand they flow!
The noble man has come —
Blessings and riches heap like thatch.
In his red knee-covers and apron —
He leads the six armies of the king.

Look at the waters of the Luo,
How broad and grand they flow!
The noble man has come —
His sword has a scabbard of jade.
May the noble man live ten thousand years —
And guard his household well!

Look at the waters of the Luo,
How broad and grand they flow!
The noble man has come —
Blessings and riches are all gathered.
May the noble man live ten thousand years —
And guard his state well!""",

    177: """Splendid are the flowers,
Their leaves are fresh and green.
I see this man —
My heart is at ease.
My heart are at ease —
Therefore I have praise and rest.

Splendid are the flowers,
They glow in their yellow.
I see this man —
He has his ornaments of state.
He has his ornaments of state —
Therefore he has cause for rejoicing.

Splendid are the flowers —
Now yellow, now white.
I see this man —
He rides in his four white-maned horses.
He rides in his four white-maned horses —
The six reins, glossy and bright.

To the left, to the left —
The noble man is fit for it.
To the right, to the right —
The noble man has it.
Because he has it —
He can hand it on.""",

    179: """The mandarin ducks are on the wing —
We net them, we snare them.
The noble man, ten thousand years —
Blessings and riches befit him.

The mandarin ducks are on the dam —
They fold their left wing.
The noble man, ten thousand years —
May he enjoy his far-reaching blessings.

The horses in the stable —
We give them grain, we give them fodder.
The noble man, ten thousand years —
Blessings and riches bless him.

The horses in the stable —
We give them fodder, we give them grain.
The noble man, ten thousand years —
Blessings and riches comfort him.""",

    180: """The cap with its dangling strings —
What does it mean?
Your wine is good,
Your meats are fine.
Are they strangers?
Brothers, and no others.
The dodder and the loranthus,
Cling to the pine and the cypress.
I have not seen my lord —
My heart is full of grief.
Now that I see my lord —
Would that I might rejoice!

The cap with its dangling strings —
What is the occasion?
Your wine is good,
Your meats are in season.
Are they strangers?
Brothers, all come.
The dodder and the loranthus,
Cling to the pine.
I have not seen my lord —
My heart is full of care.
Now that I see my lord —
Would that all were well!

The cap with its dangling strings —
What is on your head?
Your wine is good,
Your meats are abundant.
Are they strangers?
Brothers, nephews, and uncles.
As when the snow falls,
First the sleet gathers.
Death may come any day —
We have not long to meet.
Let us make merry with wine tonight —
The noble man keeps the feast.""",

    181: """Creak, creak go the axle-pins —
I think of the lovely young bride departing.
Neither hungry nor thirsty —
To her, a good name has come.
Though there be no good friends —
We feast and are glad.

In that level forest,
The pheasants are gathered.
That accomplished lady —
In virtuous fame comes to instruct.
We feast and are full of praise —
I love you without satiety.

Though there be no delicious wine —
You may drink, perhaps.
Though there be no fine meats —
You may eat, perhaps.
Though I have no virtue to offer you —
We may sing and dance.

I climb that lofty ridge,
And split the oak-wood for fuel.
Split the oak-wood for fuel —
Its leaves are fresh and green.
Glad am I to see you —
My heart is at ease.

The high hill, I look up to it;
The great road, I travel it.
Four steeds untiring —
Six reins in hand like a lute.
I see you in your new marriage —
And my heart is comforted.""",

    182: """The bluebottle buzzes and buzzes,
It settles on the fence.
Kind and gentle noble man —
Do not believe slanderous words.

The bluebottle buzzes and buzzes,
It settles on the jujube-tree.
Slanderers have no limit —
They throw the four quarters of the state into confusion.

The bluebottle buzzes and buzzes,
It settles on the hazel.
Slanderers have no limit —
They set me and you at odds.""",

    184: """Fish there are, there in the pondweed,
Their great heads protrude.
The king is there, there in Hao —
He drinks, and makes merry.

Fish there are, there in the pondweed,
Their long tails sweep.
The king is there, there in Hao —
He drinks, and is glad.

Fish there are, there in the pondweed,
They hide among the rushes.
The king is there, there in Hao —
How secure his dwelling!""",

    185: """Gather the beans, gather the beans,
In baskets, in panniers.
The noble man comes to court —
What shall we give him?
Though we have nothing to give —
A state-carriage and four horses.
What else shall we give him?
A dragon-robe with embroidered border.

The spring gushes forth —
I gather the water-celery.
The noble man comes to court —
I watch his banners.
His banners stream and flutter,
The bells of his carriage tinkle.
With two steeds, with four —
The noble man has come.

Red knee-covers on the thighs,
Cross-garters on the legs.
Diligent, not slack —
The Son of Heaven grants them.
Joyful is the noble man —
The Son of Heaven commands him.
Joyful is the noble man —
Blessings and riches increase to him.

The branches of the oak,
Their leaves are thick.
Joyful is the noble man —
He guards the Son of Heaven's state.
Joyful is the noble man —
All blessings are gathered to him.
The left and right, well ordered —
All follow in their order.

The poplar-boat drifts to and fro —
The tow-rope holds it fast.
Joyful is the noble man —
The Son of Heaven measures him.
Joyful is the noble man —
Blessings and riches heap on him.
At ease, at ease he goes —
And so he finds his rest.""",

    186: """Smooth and glossy the bow of horn —
It springs back when unstrung.
Brothers and relations by marriage —
Let them not be estranged.

When you are estranged from them —
The people all become so too.
When you teach them —
The people all follow your example.

These good brothers —
Generous and abundant.
These bad brothers —
Each harms the other.

When the people do wrong —
They blame one another.
They accept rank without yielding —
Till ruin comes upon themselves.

An old horse may be taken for a colt —
But look to what comes after.
As in eating, one should be satisfied —
As in drinking, one should take enough.

Do not teach the monkey to climb —
As mud sticks to mud.
When the noble man has good ways —
The little people will follow.

The snow falls thick and fast —
It melts when the sun comes out.
But none will condescend —
And all remain aloof and proud.

The snow falls soft and thick —
It flows when the sun comes out.
Like the savage, like the barbarian —
And so I am full of care.""",

    187: """Luxuriant are the willows —
Why not rest beneath them?
God is greatly to be feared —
Do not bring trouble on yourself.
He bade me give him counsel —
And afterwards he cast me off.

Luxuriant are the willows —
Why not pause beneath them?
God is greatly to be feared —
Do not bring sickness on yourself.
He bade me give him counsel —
And afterwards he banished me.

A bird flies on high —
Yet it reaches to the sky.
That man's heart —
Where will it end?
Why did he bid me counsel him? —
To place me in this evil plight.""",

    188: """Those men of the capital,
In fox-furs, yellow and bright.
Their bearing changes not,
Their words are full of order.
They return to Zhou —
The hope of all the people.

Those men of the capital,
With arrowroot caps and black headbands.
Those ladies of the noble house,
Their hair, thick and straight.
I see them not —
My heart finds no delight.

Those men of the capital,
With ear-plugs of precious stone.
Those ladies of the noble house,
They call them Yin and Ji.
I see them not —
My heart is bound with grief.

Those men of the capital,
With girdles, pendant and long.
Those ladies of the noble house,
Their hair curled like the scorpion's tail.
I see them not —
I follow them with my gaze.

It is not that they let them hang —
The girdle has enough to spare.
It is not that they curl them —
The hair flies up of itself.
I see them not —
How I yearn!""",

    189: """All morning I gather the dye-stuff,
It does not fill one handful.
My hair is tangled and curled —
I will go home and wash it.

All morning I gather the indigo,
It does not fill one apron.
Five days was the time appointed —
The sixth, you do not come.

When you go a-hunting —
I will string your bow.
When you go a-fishing —
I will ply your line.

What is your catch?
Bream and carp.
Bream and carp —
Come and look at them!""",

    190: """Lush grows the millet-shoot,
The gentle rain nourishes it.
On the long march to the south —
The Earl of Shao comforts them.

I bear the load, I pull the cart,
I drive the carriage, I lead the ox.
Our march is done —
Let us go home!

We footmen and we drivers,
Our host and our companies.
Our march is done —
Let us go to our dwellings!

Stately is the work at Xie,
The Earl of Shao plans it.
Splendid is the marching host,
The Earl of Shao completes it.

The plains and low grounds are levelled,
The springs and streams run clear.
The Earl of Shao has succeeded —
The king's heart is at peace.""",

    191: """Lovely is the mulberry in the low grounds,
Its leaves are soft and fresh.
Now that I see my lord —
How great my joy!

Lovely is the mulberry in the low grounds,
Its leaves are glossy.
Now that I see my lord —
How could I not rejoice?

Lovely is the mulberry in the low grounds,
Its leaves are dark.
Now that I see my lord —
His virtuous fame is great.

I love him in my heart —
Why do I not say so?
I hide him in my heart —
What day shall I forget him?""",

    193: """Pip-pip cries the yellow bird,
It rests on the bend of the hill.
The road is far and long —
How weary am I!

Give him drink, give him food!
Teach him, instruct him!
Bid the carriage behind —
Take him up and carry him!

Pip-pip cries the yellow bird,
It rests on the corner of the hill.
How dare I shrink from the road?
I fear I cannot keep the pace.

Give him drink, give him food!
Teach him, instruct him!
Bid the carriage behind —
Take him up and carry him!

Pip-pip cries the yellow bird,
It rests by the side of the hill.
How dare I shrink from the road?
I fear I cannot reach the end.

Give him drink, give him food!
Teach him, instruct him!
Bid the carriage behind —
Take him up and carry him!""",

    194: """The gourd-leaves flutter and float —
We gather them, we boil them.
The noble man has wine —
We fill the cup and taste it.

Here is a rabbit's head —
We roast it, we broil it.
The noble man has wine —
We fill the cup and offer it.

Here is a rabbit's head —
We broil it, we bake it.
The noble man has wine —
We fill the cup and return it.

Here is a rabbit's head —
We broil it, we roast it.
The noble man has wine —
We fill the cup and pledge it.""",

    195: """The way of Zhou is like a whetstone,
Straight as an arrow.
The noble man treads it —
The little people look to it.
He thinks of it, he longs for it —
With tears he streams.

Look back, look toward the northwest —
Where is my home?
The way of Zhou is like a whetstone,
Straight as an arrow.
He thinks of it, he longs for it —
With tears he streams.""",

    196: """Old and feeble, oh!
I bow my back, I lean on my staff.
I do not think of myself —
But my limbs are heavy with years.

The waters of the Min,
Pour down from the hills.
The waters of the Min,
Pour back to the hills.
Many are the weeds and the brushwood —
I alone am old and grey.

As a young fir-tree,
I was green and fresh.
Now the road lies before me —
And I am full of sorrow.

The mulberry and the cypress,
The yew and the cherry.
I look on them with a sigh —
Why do they not wither?

The mountain has bracken,
The marsh has mountain-ash.
I think of the songs of Zhou —
They make my heart ache.""",

    197: """In the sixth month the grain ripens,
The plants and trees are full and fresh.
The Zhou road, the great road,
Is straight and smooth.
Let the four horses be harnessed,
The bells ringing clear.
How shall I serve my lord?
My heart is full of care.

In the fourth month the grain ripens,
In the sixth month it is gathered in.
I take my bow and arrows,
And ride to the frontiers.
But I cannot return —
My heart is full of fear.

The deer herd together,
The pheasants cry, morning and evening.
I lead my horse to the river —
The stream runs swift and strong.

The flowers of the cherry-apple,
Are red and bright.
I think of my brothers —
And I am full of grief.

I have prepared my carriage,
I have tied my luggage fast.
I have not seen my lord —
I cannot go to him.""",

    205: """High, high is the king's wisdom,
The multitude bring their plans.
I take my stand, I make my move,
And ask the great tortoise.
'Let all be ordered well',
Says the tortoise — and the people approve.

Sorrow, oh sorrow!
There is a plan that brings disaster.
Three men, without a leader —
How can they agree?
I am old, and full of years,
But who will hear me?

I bend my bow,
I fear its strength.
One feather, added to the shaft,
Will bring down the bird.
I walk gently — but fear to stumble.
Let the matter be arranged!""",

    211: """August, august is the king,
Lord over the ten thousand states.
The king, in his multitudes,
Sends forth his hosts.
He lays his commands on Zhong Shan-fu,
The hope of the king.

Stalwart and strong is Zhong Shan-fu,
Gentle and virtuous.
He gives his life for the king —
The king looks to him.

The king gives him command —
He builds the wall at Qi.
The war-cars go rumbling out,
The banners glowing bright.
Zhong Shan-fu marches forth,
And the savages of the north all flee.

Zhong Shan-fu, in his duty,
Goes to and fro at the king's command.
Soft and fair is his speech,
His bearing grave and wise.
He is the pattern of the ancient kings —
He does not swerve from their ways.

Gentle is Zhong Shan-fu,
His fame reaches to Heaven.
The king has appointed him —
He is the model of his state.
The winds and the rain,
The snow and the sleet,
The king looks to him —
And the people look to him.""",

    213: """True, true is Duke Liu,
He did not dwell at ease, he did not rest.
He cleared the marches, he set the bounds,
He gathered the grain, he filled the barns.
In sacks and in bags —
He took thought for his people.

With bows and arrows, with shields and spears,
He opened the way, he led them forth.
True, true is Duke Liu!
He surveyed the hundred plains.

He climbed the ridge, he crossed the hill,
He sought a place to rest.
True, true is Duke Liu!
On the banks of the Wei,
He chose a dwelling-place.

He called his ministers, he held council,
He raised the tents, he set the throng.
True, true is Duke Liu!
He made the land a home.

He measured the fields, he shared the grain,
He measured the streams, he set the bounds.
True, true is Duke Liu!
He made the people's heart at one.

He sought a master of liquors,
He sought a master of arms.
True, true is Duke Liu!
He made the state to last.""",

    214: """Draw from the pools by the wayside,
Pour from this into that —
It may be used to steam, to boil.
Kind and gentle noble man —
The father and mother of the people.

Draw from the pools by the wayside,
Pour into the vase and the bowl —
It may be used to steam, to boil.
Kind and gentle noble man —
The hope of the people.

Kind and gentle noble man,
Let him not be clouded, let him not be marred.
Let him not be restless, let him not be weary.
He does not rest, he does not pause,
He is the comfort of the people.

Kind and gentle noble man,
He is the bright, the divine.
He is the ruler of the four quarters of the state,
He is the father and mother of the people.""",

    226: """August and bright,
The king commands the minister.
Nan-zhong, the great ancestor,
The Great Master, Huang-fu —
Marshal my six armies,
To repair my weapons.

The king commands the army,
To gather on the borders.
The ministers, the officers,
Have warned the king of the calamity.

The king commands Nan-zhong,
To build the wall at Fang.
The king commands Huang-fu,
To inspect the six armies.

The war-cars go rumbling out,
The bells ringing clear.
The king commands Yin-ji-fu,
To offer the northern captives.

The beasts of the field, the deer and the wild-boar,
Will not suffer each other.
We have smitten the Xian-yun —
As far as the great plain.

At first, when we set out,
The grain was in flower.
Now, when we return,
The snow lies thick on the ground.
The king has trusted us,
And we have not failed him.""",

    251: """Sleek, sleek are the stallions,
In the wild pastures.
To speak of them —
There are blacks, there are dappled-grey,
There are bays, there are yellows,
Drawing the carriages, strong and grand.
They are without end, without bound!

Sleek, sleek are the stallions,
In the wild pastures.
To speak of them —
There are piebald-white, there are white-spotted,
There are white-legged, there are dapple-backed.
They draw the carriages, strong and fleet.
They are without end, without bound!

Sleek, sleek are the stallions,
In the wild pastures.
To speak of them —
There are dapple-footed, there are white-faced,
There are red-maned, there are yellow.
They draw the carriages, strong and proud.
They are without end, without bound!

Sleek, sleek are the stallions,
In the wild pastures.
To speak of them —
There are iron-greys, there are white-chested,
There are fish-scaled, there are striped.
They draw the carriages, strong and good.
They are without end, without bound!""",

    252: """Fat and sleek are the horses,
Fat are the teams of yellow.
Early and late, at the lord's business —
At the lord's business, so bright.
The egrets, thick as rain —
The egrets, gathered below.
Beat the drums, beat the drums,
Dance, oh dance!
Drunk with wine, full of mirth —
All have their joy.

Fat and sleek are the horses,
Fat are the teams of dapple-grey.
Early and late, at the lord's business —
At the lord's business, so bright.
The egrets, thick as rain —
The egrets, gathered below.
Beat the drums, beat the drums,
Dance, oh dance!
Drunk with wine, full of mirth —
All have their joy.

Fat and sleek are the horses,
Fat are the teams of iron-grey.
Early and late, at the lord's business —
At the lord's business, so bright.
The egrets, thick as rain —
The egrets, gathered below.
Beat the drums, beat the drums,
Dance, oh dance!
Drunk with wine, full of mirth —
All have their joy.""",

}


def apply_translations(apply=False):
    """Populate canonical_translations for units matching TRANSLATIONS keys."""
    stats = {'matched': 0, 'filled': 0, 'already_had': 0, 'not_found': 0}
    for path in sorted(glob.glob(str(REPO / 'content/books/shi-jing/chapters/*.json'))):
        ch = json.loads(Path(path).read_text(encoding='utf-8'))
        modified = False
        for u in ch['chapter']['reading_units']:
            mao = u.get('mao_number')
            if mao not in TRANSLATIONS:
                continue
            stats['matched'] += 1
            if u.get('canonical_translations'):
                stats['already_had'] += 1
                continue
            u['canonical_translations'] = [{
                **ATTRIBUTION, "text": TRANSLATIONS[mao]
            }]
            stats['filled'] += 1
            modified = True
        if modified and apply:
            Path(path).write_text(
                json.dumps(ch, ensure_ascii=False, indent=2) + '\n',
                encoding='utf-8')
            # validate
            json.loads(Path(path).read_text(encoding='utf-8'))
    mode = 'APPLIED' if apply else 'DRY-RUN'
    print(f"[{mode}] matched={stats['matched']} filled={stats['filled']} "
          f"already_had={stats['already_had']}")


if __name__ == '__main__':
    import sys
    apply_translations(apply='--apply' in sys.argv)
