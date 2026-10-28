from shodoukan_practice.domain.entities import Inflection
from shodoukan_practice.domain.gateways import Morpheme
from shodoukan_practice.domain.services import (
    gap_dictionary_forms,
    gap_head,
    gap_inflection,
    is_content_word,
)


def morpheme(
    surface: str,
    lemma: str,
    pos: tuple[str, ...],
    conjugation: tuple[str, str] | None = None,
) -> Morpheme:
    return Morpheme(
        surface=surface,
        lemma=lemma,
        reading=surface,
        pos=pos,
        conjugation_type=conjugation[0] if conjugation else None,
        conjugation_form=conjugation[1] if conjugation else None,
        start=0,
        end=len(surface),
    )


VERB = ("動詞", "一般")
NOUN = ("名詞", "普通名詞", "一般")
AUXILIARY = ("助動詞",)
PAST = ("助動詞-タ", "終止形-一般")

# 引かれた: 引か + れ + た
HIKARETA = [
    morpheme("引か", "引く", VERB, ("五段-カ行", "未然形-一般")),
    morpheme("れ", "れる", AUXILIARY, ("助動詞-レル", "連用形-一般")),
    morpheme("た", "た", AUXILIARY, PAST),
]


def test_content_words_exclude_particles_and_prefixes() -> None:
    assert is_content_word(morpheme("学校", "学校", NOUN))
    assert not is_content_word(morpheme("が", "が", ("助詞", "格助詞")))
    assert not is_content_word(morpheme("お", "お", ("接頭辞",)))


def test_the_head_is_the_first_content_word() -> None:
    ocha = [morpheme("お", "お", ("接頭辞",)), morpheme("茶", "茶", NOUN)]

    assert gap_head(ocha) == ocha[1]
    assert gap_head([morpheme("が", "が", ("助詞", "格助詞"))]) is None


def test_inflection_is_the_endings_and_the_last_form() -> None:
    assert gap_inflection(HIKARETA) == Inflection(endings=("れる", "た"), form="終止形")


def test_a_word_alone_has_its_own_form() -> None:
    taberu = [morpheme("食べる", "食べる", VERB, ("下一段-バ行", "終止形-一般"))]

    assert gap_inflection(taberu) == Inflection(endings=(), form="終止形")
    assert gap_inflection([morpheme("学校", "学校", NOUN)]) == Inflection(
        endings=(), form=None
    )


def test_variants_of_the_verb_class_are_the_same_form() -> None:
    # 飲んだ: past だ is た.
    nonda = [
        morpheme("飲ん", "飲む", VERB, ("五段-マ行", "連用形-撥音便")),
        morpheme("だ", "だ", AUXILIARY, PAST),
    ]
    tabeta = [
        morpheme("食べ", "食べる", VERB, ("下一段-バ行", "連用形-一般")),
        morpheme("た", "た", AUXILIARY, PAST),
    ]
    # 読んで / 食べて: te-form で is て.
    yonde = [nonda[0], morpheme("で", "で", ("助詞", "接続助詞"))]
    tabete = [tabeta[0], morpheme("て", "て", ("助詞", "接続助詞"))]
    # 食べられた / 引かれた: られる is れる.
    taberareta = [
        tabeta[0],
        morpheme("られ", "られる", AUXILIARY, ("助動詞-レル", "連用形-一般")),
        HIKARETA[2],
    ]

    assert gap_inflection(nonda) == gap_inflection(tabeta)
    assert gap_inflection(yonde) == gap_inflection(tabete)
    assert gap_inflection(taberareta) == gap_inflection(HIKARETA)


def test_the_copula_da_is_not_the_past() -> None:
    # 静かな: な is the copula だ, not past た.
    shizukana = [
        morpheme("静か", "静か", ("形状詞", "一般")),
        morpheme("な", "だ", AUXILIARY, ("助動詞-ダ", "連体形-一般")),
    ]

    assert gap_inflection(shizukana) == Inflection(endings=("だ",), form="連体形")


def test_a_case_particle_de_stays_de() -> None:
    gakkou_de = [
        morpheme("学校", "学校", NOUN),
        morpheme("で", "で", ("助詞", "格助詞")),
    ]

    assert gap_inflection(gakkou_de) == Inflection(endings=("で",), form=None)


def test_no_head_no_inflection() -> None:
    assert gap_inflection([morpheme("が", "が", ("助詞", "格助詞"))]) is None


def test_dictionary_forms() -> None:
    # 共に: a word of two morphemes; いけない: an expression ending in ない.
    tomoni = [morpheme("共", "共", NOUN), morpheme("に", "に", ("助詞", "格助詞"))]
    ikenai = [
        morpheme("いけ", "いける", VERB, ("下一段-カ行", "未然形-一般")),
        morpheme("ない", "ない", AUXILIARY, ("助動詞-ナイ", "終止形-一般")),
    ]

    assert gap_dictionary_forms(HIKARETA) == ["引く", "引かれた"]
    assert gap_dictionary_forms(tomoni) == ["共", "共に"]
    assert gap_dictionary_forms(ikenai) == ["いける", "いけない"]
    assert gap_dictionary_forms([]) == []


def test_suffixes_and_compounds_are_part_of_the_word() -> None:
    # 七つ: 七 + the counter つ; 勉強した: 勉強 + し + た.
    nanatsu = [
        morpheme("七", "七", ("名詞", "数詞")),
        morpheme("つ", "つ", ("接尾辞", "名詞的", "助数詞")),
    ]
    benkyou_shita = [
        morpheme("勉強", "勉強", NOUN),
        morpheme("し", "する", VERB, ("サ行変格", "連用形-一般")),
        morpheme("た", "た", AUXILIARY, PAST),
    ]

    assert gap_inflection(nanatsu) == Inflection(endings=(), form=None)
    assert gap_inflection(benkyou_shita) == Inflection(endings=("た",), form="終止形")


def test_attributive_and_conclusive_are_one_form_except_for_the_copula() -> None:
    # 走った人 (連体形) is written like 走った。 (終止形); 静かな isn't 静かだ.
    hashitta = [
        morpheme("走っ", "走る", VERB, ("五段-ラ行", "連用形-促音便")),
        morpheme("た", "た", AUXILIARY, ("助動詞-タ", "連体形-一般")),
    ]
    takai = [morpheme("高い", "高い", ("形容詞", "一般"), ("形容詞", "連体形-一般"))]
    shizukana = [
        morpheme("静か", "静か", ("形状詞", "一般")),
        morpheme("な", "だ", AUXILIARY, ("助動詞-ダ", "連体形-一般")),
    ]

    assert gap_inflection(hashitta) == Inflection(endings=("た",), form="終止形")
    assert gap_inflection(takai) == Inflection(endings=(), form="終止形")
    assert gap_inflection(shizukana) == Inflection(endings=("だ",), form="連体形")
