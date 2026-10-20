"""Manim visuals for the FDE project video (house style: 3b1b manimgl, 16:9, dark canvas, Inter Tight).

Draft timing is self-paced. After she records the voiceover, add Timed.until() cues per scene
(same pattern as DL-jargon-manim/reel.py) so every beat lands on her words.

Render one:  ~/.manimgl-venv/bin/manimgl fde_visuals.py Architecture -w
Scenes 05b CostCompare and 10 Evals read real numbers from numbers.json (filled from the actual eval run).
"""
from manimlib import *
import json
import os
import manimpango

HERE = os.path.dirname(os.path.abspath(__file__))
manimpango.register_font(os.path.join(HERE, "intertight.ttf"))

BLUE_N = "#58C4DD"
YEL = "#FFFF00"
RED_E = "#FC6255"
GRN = "#83C167"
PUR = "#C08CFF"
EDGE = "#5a6170"
FONT = "Inter Tight"


# ------------------------------------------------------------------ helpers
def T(s, size=0.5, color=WHITE, bold=False):
    return Text(s, font=FONT, weight=BOLD if bold else NORMAL).scale(size).set_color(color)


def title(s):
    return T(s, 0.9, WHITE, bold=True).to_edge(UP, buff=0.5)


def box(label, color=BLUE_N, w=2.6, h=0.9, size=0.42, sub=None):
    r = RoundedRectangle(width=w, height=h, corner_radius=0.16).set_stroke(color, 3).set_fill(color, 0.12)
    t = T(label, size, WHITE, bold=True)
    if t.get_width() > w - 0.3:
        t.set_width(w - 0.3)
    g = VGroup(r, t)
    if sub:
        st = T(sub, max(size * 0.72, 0.27), GREY_A)
        if st.get_width() > w - 0.3:
            st.set_width(w - 0.3)
        VGroup(t, st).arrange(DOWN, buff=0.08).move_to(r)
        g.add(st)
    return g


def arrow(a, b, color=EDGE, buff=0.12):
    return Arrow(a.get_center(), b.get_center(), buff=buff).set_color(color)


def edge_arrow(a, b, color=EDGE):
    """Arrow from the edge of a to the edge of b."""
    return Arrow(a, b, buff=0.1).set_color(color)


def flow(ar, color=YEL):
    return ShowPassingFlash(ar.copy().set_stroke(color, 7), time_width=0.6)


def step(s, color=GREY_A):
    return T(s, 0.48, color, bold=True).to_edge(DOWN, buff=0.45)


def swap(old, new):
    return [FadeOut(old, shift=0.15 * UP), FadeIn(new, shift=0.15 * UP)]


def chip(s, color):
    t = T(s, 0.36, color, bold=True)
    r = SurroundingRectangle(t, buff=0.1).set_stroke(color, 2).set_fill("#0f1117", 0.9)
    return VGroup(r, t)


# ------------------------------------------------------------- 00 hook flow
class HookFlow(Scene):
    def construct(self):
        mail = box("New email", BLUE_N, 2.6, 1.0, sub='"pump making a grinding noise"').move_to(5.0 * LEFT + 1.2 * UP)
        clf = box("Classifier", PUR, 2.4, 1.0, sub="service_booking · 0.97").move_to(1.8 * LEFT + 1.2 * UP)
        db = box("Pump history", BLUE_N, 2.4, 0.8).move_to(1.6 * RIGHT + 2.6 * UP)
        rag = box("Manual + warranty", BLUE_N, 2.4, 0.8).move_to(1.6 * RIGHT + 1.2 * UP)
        cal = box("2 free slots", BLUE_N, 2.4, 0.8).move_to(1.6 * RIGHT + 0.2 * DOWN)
        draft = box("Draft reply", GRN, 2.4, 1.0).move_to(5.0 * RIGHT + 1.2 * UP)
        gate = box("You approve", YEL, 2.6, 0.9).move_to(5.0 * RIGHT + 1.6 * DOWN)
        acts = VGroup(chip("email sent", GRN), chip("visit booked", GRN), chip("logged", GRN)).arrange(RIGHT, buff=0.3).move_to(2.9 * DOWN + 1.8 * RIGHT)
        a1 = edge_arrow(mail.get_right(), clf.get_left())
        a2 = VGroup(*[edge_arrow(clf.get_right(), x.get_left()) for x in (db, rag, cal)])
        a3 = VGroup(*[edge_arrow(x.get_right(), draft.get_left()) for x in (db, rag, cal)])
        a4 = edge_arrow(draft.get_bottom(), gate.get_top())
        a5 = edge_arrow(gate.get_left(), acts.get_right() + 0.1 * RIGHT)

        self.play(FadeIn(mail, shift=0.3 * RIGHT), run_time=0.6)
        self.play(GrowArrow(a1), FadeIn(clf, scale=0.9), run_time=0.6)
        self.play(flow(a1))
        self.play(LaggedStart(*[GrowArrow(a) for a in a2], lag_ratio=0.15), LaggedStart(*[FadeIn(x, shift=0.2 * RIGHT) for x in (db, rag, cal)], lag_ratio=0.15), run_time=0.9)
        self.play(*[flow(a) for a in a2], run_time=0.8)
        self.play(LaggedStart(*[GrowArrow(a) for a in a3], lag_ratio=0.1), FadeIn(draft, scale=0.9), run_time=0.8)
        self.play(*[flow(a, GRN) for a in a3], run_time=0.8)
        self.play(GrowArrow(a4), FadeIn(gate, scale=0.9), run_time=0.6)
        self.play(Indicate(gate, color=YEL), run_time=0.8)
        self.play(GrowArrow(a5), LaggedStart(*[FadeIn(c, scale=1.2) for c in acts], lag_ratio=0.25), run_time=1.0)
        self.wait(1)


# ------------------------------------------------------------- 01 FDE loop
class FDELoop(Scene):
    def construct(self):
        ttl = title("What an FDE actually does")
        roles = VGroup(
            box("Software engineer", BLUE_N, 3.4, 1.1, sub="builds the product"),
            box("ML engineer", PUR, 3.4, 1.1, sub="builds the models"),
            box("Forward Deployed Engineer", YEL, 3.8, 1.1, sub="makes AI work inside a client"),
        ).arrange(RIGHT, buff=0.5).move_to(1.2 * UP)
        self.play(Write(ttl), run_time=0.8)
        self.play(LaggedStart(*[FadeIn(r, shift=0.2 * UP) for r in roles], lag_ratio=0.3), run_time=1.4)
        self.wait(0.6)
        self.play(roles[:2].animate.set_opacity(0.3), Indicate(roles[2], color=YEL, scale_factor=1.05), run_time=0.8)

        names = ["Client", "Scope", "Build", "Deploy", "Prove"]
        cols = [BLUE_N, PUR, BLUE_N, GRN, YEL]
        center, R = 0.35 * DOWN, 1.65
        nodes = VGroup()
        for i, (n, c) in enumerate(zip(names, cols)):
            ang = PI / 2 - i * TAU / 5
            nodes.add(box(n, c, 1.7, 0.62, 0.36).move_to(center + R * np.array([1.9 * np.cos(ang), np.sin(ang), 0])))
        arcs = VGroup(*[
            CurvedArrow(nodes[i].get_center(), nodes[(i + 1) % 5].get_center(), angle=-TAU / 7).set_color(EDGE)
            for i in range(5)
        ])
        for a in arcs:
            a.scale(0.62)
        self.play(FadeOut(roles), FadeOut(ttl), run_time=0.6)
        loop_t = title("The FDE loop")
        self.play(Write(loop_t), LaggedStart(*[FadeIn(n, scale=0.9) for n in nodes], lag_ratio=0.2), run_time=1.4)
        self.play(LaggedStart(*[ShowCreation(a) for a in arcs], lag_ratio=0.2), run_time=1.4)
        for _ in range(2):
            self.play(LaggedStart(*[flow(a) for a in arcs], lag_ratio=0.2), run_time=1.4)
        self.wait(1)


# ---------------------------------------------------------- 02 discovery
class Discovery(Scene):
    def construct(self):
        ask = T('"We want AI to handle our customer emails."', 0.62, WHITE, bold=True).move_to(2.6 * UP)
        self.play(Write(ask), run_time=1.6)
        self.wait(0.5)
        qs = [("How many emails a day?", "about 300"),
              ("What kinds?", "orders · noise · bookings · warranty · complaints"),
              ("Who answers them today?", "a small support team"),
              ("How long does a reply take?", "1–2 days"),
              ("Where does the data live?", "3 different places")]
        rows = VGroup()
        for q, a in qs:
            rows.add(VGroup(T(q, 0.46, BLUE_N, bold=True), T(a, 0.42, GREY_A)).arrange(RIGHT, buff=0.4))
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.32).move_to(0.6 * DOWN)
        cap = step("1. ask questions until the vague ask is buildable")
        self.play(FadeIn(cap, shift=0.15 * UP), run_time=0.4)
        for r in rows:
            self.play(FadeIn(r[0], shift=0.15 * RIGHT), run_time=0.45)
            self.play(Write(r[1]), run_time=0.5)
        self.play(Indicate(rows[-1], color=YEL), run_time=1.0)
        self.wait(1)


class TodayVsTarget(Scene):
    def construct(self):
        t1 = T("Today", 0.6, RED_E, bold=True).move_to(5.6 * LEFT + 1.8 * UP)
        mail = box("Email", BLUE_N, 1.5, 0.7, 0.36).move_to(3.6 * LEFT + 1.8 * UP)
        human = box("Person", RED_E, 1.5, 0.7, 0.36).move_to(1.4 * LEFT + 1.8 * UP)
        sys3 = VGroup(*[box(s, EDGE, 1.9, 0.55, 0.3) for s in ("Access DB export", "Excel orders", "PDF manuals")]).arrange(DOWN, buff=0.12).move_to(1.4 * RIGHT + 1.8 * UP)
        rep = box("Reply", RED_E, 1.5, 0.7, 0.36, sub="1–2 days").move_to(4.3 * RIGHT + 1.8 * UP)
        top = VGroup(t1, mail, human, sys3, rep)
        a = [edge_arrow(mail.get_right(), human.get_left()), edge_arrow(human.get_right(), sys3.get_left()), edge_arrow(sys3.get_right(), rep.get_left())]
        self.play(FadeIn(t1), LaggedStart(*[FadeIn(x, shift=0.2 * RIGHT) for x in (mail, human, sys3, rep)], lag_ratio=0.3), *[GrowArrow(x) for x in a], run_time=2.0)
        self.play(*[flow(x, RED_E) for x in a], run_time=1.2)

        t2 = T("Target", 0.6, GRN, bold=True).move_to(5.6 * LEFT + 1.4 * DOWN)
        mail2 = box("Email", BLUE_N, 1.5, 0.7, 0.36).move_to(3.6 * LEFT + 1.4 * DOWN)
        cop = box("Copilot", BLUE_N, 1.9, 0.7, 0.36, sub="looks it all up").move_to(1.2 * LEFT + 1.4 * DOWN)
        appr = box("Person approves", YEL, 2.2, 0.7, 0.32).move_to(1.6 * RIGHT + 1.4 * DOWN)
        rep2 = box("Reply", GRN, 1.5, 0.7, 0.36, sub="< 1 minute").move_to(4.3 * RIGHT + 1.4 * DOWN)
        b = [edge_arrow(mail2.get_right(), cop.get_left()), edge_arrow(cop.get_right(), appr.get_left()), edge_arrow(appr.get_right(), rep2.get_left())]
        self.play(FadeIn(t2), LaggedStart(*[FadeIn(x, shift=0.2 * RIGHT) for x in (mail2, cop, appr, rep2)], lag_ratio=0.3), *[GrowArrow(x) for x in b], run_time=2.0)
        self.play(*[flow(x, GRN) for x in b], run_time=1.0)
        self.wait(1)


# ------------------------------------------------------- 03 architecture
class Architecture(Scene):
    def construct(self):
        ttl = title("Legacy → modern: the architecture")
        self.play(Write(ttl), run_time=0.8)
        legacy = VGroup(*[box(s, RED_E, 2.3, 0.55, 0.3) for s in ("legacy.db (Access)", "Excel exports", "PDF manuals")]).arrange(DOWN, buff=0.14).move_to(5.6 * LEFT + 0.9 * UP)
        leg_lbl = T("legacy", 0.36, RED_E).next_to(legacy, UP, buff=0.12)
        mig = box("Migration", EDGE, 1.7, 0.6, 0.32).move_to(3.1 * LEFT + 1.6 * UP)
        pg = box("Postgres", BLUE_N, 2.1, 0.8, 0.38, sub="read-only views").move_to(0.6 * LEFT + 2.0 * UP)
        vec = box("Chroma", BLUE_N, 2.1, 0.8, 0.38, sub="manual + warranty chunks").move_to(0.6 * LEFT + 0.4 * DOWN)
        gmail = box("Gmail", GRN, 1.6, 0.6, 0.34).move_to(5.6 * LEFT + 2.0 * DOWN)
        clf = box("Fine-tuned classifier", PUR, 2.6, 0.8, 0.34).move_to(2.9 * LEFT + 2.0 * DOWN)
        agent = box("Agent (LangGraph)", YEL, 2.8, 1.0, 0.4).move_to(2.6 * RIGHT + 0.4 * DOWN)
        mcp = VGroup(*[box(s, BLUE_N, 2.2, 0.55, 0.3) for s in ("MCP: company-db", "MCP: gmail", "MCP: calendar")]).arrange(DOWN, buff=0.14).move_to(2.6 * RIGHT + 2.0 * UP)
        gate = box("Human approval", YEL, 2.4, 0.7, 0.34).move_to(5.6 * RIGHT + 0.4 * DOWN)
        audit = box("Audit log", EDGE, 1.8, 0.55, 0.3).move_to(5.6 * RIGHT + 2.0 * DOWN)
        evals = box("Evals + CI/CD", GRN, 2.2, 0.55, 0.3).move_to(2.6 * RIGHT + 2.6 * DOWN)

        cap = step("1. clean the legacy data", RED_E)
        self.play(FadeIn(cap), LaggedStart(*[FadeIn(x, shift=0.2 * RIGHT) for x in legacy], lag_ratio=0.2), FadeIn(leg_lbl), run_time=1.0)
        a_mig = [edge_arrow(legacy.get_right(), mig.get_left()), edge_arrow(mig.get_right(), pg.get_left()), edge_arrow(legacy[2].get_right(), vec.get_left())]
        self.play(FadeIn(mig), FadeIn(pg, scale=0.9), FadeIn(vec, scale=0.9), *[GrowArrow(a) for a in a_mig], run_time=1.2)
        self.play(*[flow(a) for a in a_mig], legacy.animate.set_opacity(0.45), run_time=1.0)

        cap2 = step("2. sort every email with a fine-tuned model", PUR)
        a_in = [edge_arrow(gmail.get_right(), clf.get_left()), edge_arrow(clf.get_right(), agent.get_left())]
        self.play(*swap(cap, cap2), FadeIn(gmail), FadeIn(clf, scale=0.9), *[GrowArrow(a) for a in a_in], run_time=1.0)
        self.play(*[flow(a) for a in a_in], run_time=0.8)

        cap3 = step("3. give the agent tools through MCP", BLUE_N)
        a_tools = [edge_arrow(agent.get_top(), mcp.get_bottom()), edge_arrow(mcp.get_left(), pg.get_right()), edge_arrow(agent.get_left() + 0.2 * UP, vec.get_right())]
        self.play(*swap(cap2, cap3), FadeIn(agent, scale=0.9), LaggedStart(*[FadeIn(m, shift=0.15 * DOWN) for m in mcp], lag_ratio=0.2), *[GrowArrow(a) for a in a_tools], run_time=1.4)
        self.play(*[flow(a) for a in a_tools], run_time=0.9)

        cap4 = step("4. a person approves anything that acts", YEL)
        a_out = [edge_arrow(agent.get_right(), gate.get_left()), edge_arrow(gate.get_bottom(), audit.get_top()), edge_arrow(agent.get_bottom(), evals.get_top())]
        self.play(*swap(cap3, cap4), FadeIn(gate, scale=0.9), FadeIn(audit), FadeIn(evals), *[GrowArrow(a) for a in a_out], run_time=1.2)
        self.play(Indicate(gate, color=YEL), *[flow(a, GRN) for a in a_out], run_time=1.0)
        self.wait(1.5)


# ---------------------------------------------------------- 04 migration
class Migration(Scene):
    def construct(self):
        ttl = title("Legacy data → clean tables")
        self.play(Write(ttl), run_time=0.7)
        hdr = ["job_id", "cust", "date", "pump", "status", "notes"]
        data = [["101", "R. Kulkarni", "03/04/19", "VP-200", "done", "noise"],
                ["102", "Kulkarni R", "2019-04-12", "VP200", "Completed", "-"],
                ["103", "Shah Ind.", "12 Apr 2019", "VP-350", "closed", "seal"],
                ["104", "Shah Industries", "04/13/2019", "vp350", "DONE", "?"]]
        cw, ch = 1.55, 0.5
        cells = VGroup()
        bad = []
        for r, row in enumerate([hdr] + data):
            for c, v in enumerate(row):
                rect = Rectangle(width=cw, height=ch).set_stroke(EDGE, 1.5).move_to([(c - 2.5) * cw, 1.5 - r * ch, 0])
                txt = T(v, 0.3, WHITE if r else BLUE_N, bold=(r == 0)).move_to(rect)
                if txt.get_width() > cw - 0.12:
                    txt.set_width(cw - 0.12)
                cells.add(VGroup(rect, txt))
                if r and c in (1, 2, 3, 4):
                    bad.append(rect)
        cap = step("one wide table · mixed dates · free-text status · duplicate customers", RED_E)
        self.play(LaggedStart(*[FadeIn(x) for x in cells], lag_ratio=0.01), FadeIn(cap), run_time=1.4)
        self.play(*[b.animate.set_fill(RED_E, 0.25).set_stroke(RED_E, 2) for b in bad], run_time=1.0)
        self.wait(0.8)

        tables = VGroup(*[box(n, BLUE_N, 2.2, 0.8, 0.38, sub=s) for n, s in [
            ("customers", "deduplicated"), ("pumps", "one model code"), ("orders", "ISO dates"),
            ("service_tickets", "one status set"), ("technicians", "skills")]]).arrange(RIGHT, buff=0.25).move_to(0.5 * UP)
        cap2 = step("clean, split, deduplicated · agent gets read-only views", GRN)
        self.play(*swap(cap, cap2), ReplacementTransform(cells, tables), run_time=1.6)
        lock = chip("agent: read-only", YEL).next_to(tables, DOWN, buff=0.5)
        self.play(LaggedStart(*[t[0].animate.set_stroke(GRN, 3) for t in tables], lag_ratio=0.1), FadeIn(lock, scale=1.2), run_time=1.0)
        self.wait(1.2)


# --------------------------------------------------------- 05 classifier
class Classifier(Scene):
    def construct(self):
        ttl = title("A small fine-tuned classifier")
        self.play(Write(ttl), run_time=0.7)
        email = box("Email", BLUE_N, 3.6, 1.1, 0.4, sub='"My VP-100 is making a rattling sound, like gravel inside"').move_to(4.3 * LEFT + 0.4 * UP)
        model = box("DistilBERT", PUR, 2.4, 1.6, 0.48, sub="fine-tuned on labelled emails").move_to(0.6 * LEFT + 0.4 * UP)
        intents = ["technical_question", "warranty_claim", "service_booking", "order_status", "complaint", "other"]
        probs = [0.977, 0.01, 0.006, 0.004, 0.002, 0.001]  # measured on demo email m010 (technical_question 97.7%), other bars shown small
        rows = VGroup()
        for name, p in zip(intents, probs):
            lbl = T(name, 0.32, GREY_A)
            bar = Rectangle(width=max(0.06, 3.0 * p), height=0.28).set_stroke(width=0).set_fill(YEL if p > 0.5 else EDGE, 0.9)
            rows.add(VGroup(lbl, bar).arrange(RIGHT, buff=0.2, aligned_edge=DOWN))
        for r in rows:
            r[0].set_width(min(r[0].get_width(), 2.4))
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.16).move_to(4.0 * RIGHT + 0.4 * UP)
        a1 = edge_arrow(email.get_right(), model.get_left())
        a2 = edge_arrow(model.get_right(), rows.get_left())
        self.play(FadeIn(email, shift=0.2 * RIGHT), run_time=0.6)
        self.play(GrowArrow(a1), FadeIn(model, scale=0.9), run_time=0.7)
        self.play(flow(a1), Indicate(model, color=PUR, scale_factor=1.03), run_time=1.0)
        self.play(GrowArrow(a2), LaggedStart(*[GrowFromEdge(r[1], LEFT) for r in rows], lag_ratio=0.1), LaggedStart(*[FadeIn(r[0]) for r in rows], lag_ratio=0.1), run_time=1.2)
        self.play(rows[0][0].animate.set_color(YEL), run_time=0.4)
        why = VGroup(chip("cheap per email", GRN), chip("fast", GRN), chip("consistent labels", GRN), chip("runs on their server", GRN)).arrange(RIGHT, buff=0.3).move_to(2.2 * DOWN)
        self.play(LaggedStart(*[FadeIn(c, shift=0.15 * UP) for c in why], lag_ratio=0.2), run_time=1.2)
        self.wait(1.2)


# ---------------------------------------------------------------- 06 RAG
class RAG(Scene):
    def construct(self):
        ttl = title("RAG with citations")
        self.play(Write(ttl), run_time=0.7)
        doc = VGroup(*[box(s, BLUE_N, 2.6, 0.5, 0.28) for s in ("VP-100 manual · Install", "VP-100 manual · Noise & vibration", "VP-100 manual · Maintenance", "Warranty · What's covered", "Warranty · Exclusions")]).arrange(DOWN, buff=0.1).move_to(4.6 * LEFT + 0.2 * DOWN)
        cap = step("1. split by headings, so each section stays whole")
        self.play(FadeIn(cap), LaggedStart(*[FadeIn(d, shift=0.15 * RIGHT) for d in doc], lag_ratio=0.15), run_time=1.2)
        plane = Rectangle(width=4.2, height=4.0).set_stroke(EDGE, 1.5).move_to(0.6 * RIGHT + 0.2 * DOWN)
        pts = [(-1.5, 1.3), (0.8, -0.4), (-0.5, -1.4), (1.5, 1.2), (1.7, 0.6)]
        dots = VGroup(*[Dot(plane.get_center() + np.array([x, y, 0]), radius=0.1).set_color(BLUE_N) for x, y in pts])
        cap2 = step("2. embed each chunk (local model) and store it in Chroma")
        self.play(*swap(cap, cap2), ShowCreation(plane), *[TransformFromCopy(d, p) for d, p in zip(doc, dots)], run_time=1.4)
        q = Dot(plane.get_center() + np.array([0.6, -0.15, 0]), radius=0.13).set_color(YEL)
        ql = T('"rattling noise like gravel"', 0.34, YEL).next_to(plane, UP, buff=0.15)
        cap3 = step("3. the question lands next to the right section", YEL)
        self.play(*swap(cap2, cap3), FadeIn(q, scale=2), Write(ql), run_time=1.0)
        circ = Circle(radius=0.75).set_stroke(YEL, 2).move_to(q)
        self.play(ShowCreation(circ), dots[1].animate.set_color(GRN).scale(1.4), doc[1][0].animate.set_stroke(GRN, 4), run_time=1.0)
        ans = box("Answer", GRN, 3.6, 1.2, 0.42, sub="source: VP-100 manual · Noise & vibration").move_to(4.9 * RIGHT + 0.2 * DOWN)
        a_ans = edge_arrow(plane.get_right(), ans.get_left(), GRN)
        self.play(GrowArrow(a_ans), run_time=0.4)
        self.play(FadeIn(ans, shift=0.2 * UP), run_time=0.8)
        self.wait(1.2)


# ---------------------------------------------------------------- 07 MCP
class MCP(Scene):
    def construct(self):
        ttl = title("MCP: giving the agent tools")
        self.play(Write(ttl), run_time=0.7)
        agent = box("Agent", YEL, 2.2, 1.0, 0.46).move_to(5.0 * LEFT + 0.2 * DOWN)
        servers = [("company-db", ["get_customer", "get_order_status", "get_pump_history", "create_service_ticket"], BLUE_N),
                   ("gmail", ["list_unread", "get_email", "create_draft", "send_draft (after approval)"], GRN),
                   ("calendar", ["find_free_slots", "create_event"], PUR)]
        cols = VGroup()
        for name, tools, c in servers:
            head = box("MCP · " + name, c, 3.2, 0.7, 0.36)
            tl = VGroup(*[T(t, 0.3, GREY_A) for t in tools]).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
            cols.add(VGroup(head, tl).arrange(DOWN, buff=0.18))
        cols.arrange(DOWN, buff=0.35, aligned_edge=LEFT).move_to(0.6 * RIGHT + 0.1 * DOWN)
        systems = VGroup(box("Postgres", BLUE_N, 1.9, 0.6, 0.32), box("Gmail", GRN, 1.9, 0.6, 0.32), box("Google Calendar", PUR, 2.2, 0.6, 0.3))
        for s, col in zip(systems, cols):
            s.move_to([5.2, col[0].get_y(), 0])
        self.play(FadeIn(agent, scale=0.9), run_time=0.5)
        ars = [edge_arrow(agent.get_right(), col[0].get_left()) for col in cols]
        ars2 = [edge_arrow(col[0].get_right(), s.get_left()) for col, s in zip(cols, systems)]
        for col, a, a2, s in zip(cols, ars, ars2, systems):
            self.play(GrowArrow(a), FadeIn(col[0], shift=0.15 * RIGHT), run_time=0.6)
            self.play(LaggedStart(*[FadeIn(t, shift=0.1 * RIGHT) for t in col[1]], lag_ratio=0.15), GrowArrow(a2), FadeIn(s), run_time=0.9)
        self.play(*[flow(a) for a in ars], run_time=0.8)
        self.play(*[flow(a, GRN) for a in ars2], run_time=0.8)
        lock = chip("read-only DB login", YEL).next_to(systems[0], UP, buff=0.15)
        mock = chip("mock mode: local JSON · real mode: Google API", GREY_A).to_edge(DOWN, buff=0.45)
        self.play(FadeIn(lock, scale=1.2), FadeIn(mock, shift=0.15 * UP), run_time=0.8)
        self.wait(1.2)


# --------------------------------------------------------- 08 agent routing
class AgentRouting(Scene):
    def construct(self):
        ttl = title("The agent: route, draft, approve")
        self.play(Write(ttl), run_time=0.7)
        clf = box("Classifier", PUR, 2.0, 0.8, 0.38).move_to(5.4 * LEFT + 0.2 * DOWN)
        routes = [("order_status", "company-db lookup", BLUE_N), ("technical / warranty", "RAG + pump history", BLUE_N),
                  ("service_booking", "calendar: 2 slots", BLUE_N), ("complaint", "ticket + a person", RED_E), ("other", "holding reply", EDGE)]
        rb = VGroup(*[box(a, c, 2.6, 0.62, 0.3, sub=b) for a, b, c in routes]).arrange(DOWN, buff=0.16).move_to(1.6 * LEFT + 0.2 * DOWN)
        draft = box("Draft", GRN, 1.8, 0.8, 0.38).move_to(2.1 * RIGHT + 0.6 * UP)
        gate = box("Approve?", YEL, 2.0, 0.8, 0.38).move_to(4.9 * RIGHT + 0.6 * UP)
        act = box("Send + book", GRN, 2.0, 0.7, 0.34).move_to(4.9 * RIGHT + 1.0 * DOWN)
        human = box("Person handles it", RED_E, 2.4, 0.7, 0.32).move_to(2.3 * RIGHT + 2.3 * DOWN)
        log = chip("every step → audit log", GREY_A).to_edge(DOWN, buff=0.4).shift(3.5 * RIGHT)
        a_r = [edge_arrow(clf.get_right(), r.get_left()) for r in rb]
        self.play(FadeIn(clf, scale=0.9), run_time=0.5)
        self.play(*[GrowArrow(a) for a in a_r], LaggedStart(*[FadeIn(r, shift=0.15 * RIGHT) for r in rb], lag_ratio=0.12), run_time=1.3)
        a_d = [edge_arrow(rb[i].get_right(), draft.get_left()) for i in (0, 1, 2, 4)]
        a_c = edge_arrow(rb[3].get_right(), human.get_left(), RED_E)
        self.play(*[GrowArrow(a) for a in a_d], FadeIn(draft), GrowArrow(a_c), FadeIn(human), run_time=1.0)
        self.play(*[flow(a) for a in a_d], flow(a_c, RED_E), run_time=1.0)
        a_g = edge_arrow(draft.get_right(), gate.get_left())
        a_a = edge_arrow(gate.get_bottom(), act.get_top(), GRN)
        self.play(GrowArrow(a_g), FadeIn(gate, scale=0.9), run_time=0.6)
        self.play(Indicate(gate, color=YEL), run_time=0.8)
        self.play(GrowArrow(a_a), FadeIn(act), FadeIn(log), run_time=0.8)
        self.play(flow(a_g), flow(a_a, GRN), run_time=0.9)
        self.wait(1.2)


# -------------------------------------------------------------- 11 deploy
class Deploy(Scene):
    def construct(self):
        ttl = title("Deploy with an eval gate")
        self.play(Write(ttl), run_time=0.7)
        push = box("git push", BLUE_N, 1.8, 0.7, 0.36).move_to(5.4 * LEFT + 0.4 * UP)
        tests = box("Tests", BLUE_N, 1.6, 0.7, 0.36).move_to(2.7 * LEFT + 0.4 * UP)
        ev = box("Evals", YEL, 1.8, 0.9, 0.38, sub="accuracy ≥ agreed bar").move_to(0.0 * LEFT + 0.4 * UP)
        dep = box("docker compose up", GRN, 2.6, 0.7, 0.34).move_to(3.4 * RIGHT + 0.4 * UP)
        srv = box("Client's server", GRN, 2.2, 0.7, 0.34).move_to(3.4 * RIGHT + 1.6 * DOWN)
        stop = box("Build fails", RED_E, 2.0, 0.7, 0.34).move_to(0.0 * LEFT + 2.0 * DOWN)
        a = [edge_arrow(push.get_right(), tests.get_left()), edge_arrow(tests.get_right(), ev.get_left()), edge_arrow(ev.get_right(), dep.get_left()), edge_arrow(dep.get_bottom(), srv.get_top())]
        af = edge_arrow(ev.get_bottom(), stop.get_top(), RED_E)
        self.play(LaggedStart(*[FadeIn(x, shift=0.15 * RIGHT) for x in (push, tests, ev, dep, srv)], lag_ratio=0.2), *[GrowArrow(x) for x in a], run_time=1.6)
        self.play(*[flow(x, GRN) for x in a], run_time=1.2)
        cap = step('a "small prompt tweak" that breaks warranty answers…', RED_E)
        self.play(FadeIn(cap), GrowArrow(af), FadeIn(stop, scale=1.1), run_time=0.8)
        self.play(flow(af, RED_E), Indicate(stop, color=RED_E), run_time=1.0)
        self.wait(1.2)


# ------------------------------------------------------------- 12 roadmap
class Roadmap(Scene):
    def construct(self):
        ttl = title("Every chapter is an FDE skill")
        self.play(Write(ttl), run_time=0.7)
        skills = ["Scoping a vague ask", "SQL + data migration", "Fine-tuning small models", "RAG with citations",
                  "Tools with MCP", "Agents + human approval", "Evals + cost", "Docker + CI/CD"]
        cols = [BLUE_N, BLUE_N, PUR, BLUE_N, BLUE_N, YEL, GRN, GRN]
        nodes = VGroup()
        for i, (s, c) in enumerate(zip(skills, cols)):
            x = -5.6 + i * 1.6
            y = 0.9 if i % 2 == 0 else -0.9
            d = Circle(radius=0.38).set_stroke(c, 4).set_fill("#0f1117", 1).move_to([x, y, 0])
            lbl = T(s, 0.34, WHITE, bold=True).next_to(d, UP if i % 2 == 0 else DOWN, buff=0.2)
            if lbl.get_width() > 2.4:
                lbl.set_width(2.4)
            num = T(f"{i + 1:02d}", 0.4, c, bold=True).move_to(d)
            nodes.add(VGroup(d, lbl, num))
        path = VMobject().set_points_smoothly([n[0].get_center() for n in nodes]).set_stroke(EDGE, 3)
        self.play(ShowCreation(path), run_time=1.2)
        for n in nodes:
            self.play(FadeIn(n[0], scale=0.6), FadeIn(n[2]), Write(n[1]), run_time=0.45)
        self.play(ShowPassingFlash(path.copy().set_stroke(YEL, 8), time_width=0.4), run_time=1.6)
        self.wait(1.2)


# --------------------------------------------- 05b + 10: real numbers only
def load_numbers():
    p = os.path.join(HERE, "numbers.json")
    if not os.path.exists(p):
        raise SystemExit("numbers.json missing: fill it from the real eval run (see project/README.md) before rendering this scene.")
    return json.load(open(p))


class CostCompare(Scene):
    def construct(self):
        n = load_numbers()["classifier_vs_llm"]
        ttl = title("Fine-tuned model vs asking an LLM")
        self.play(Write(ttl), run_time=0.7)
        metrics = [("accuracy", "%"), ("latency", " ms/email"), ("cost", " per 1K emails")]
        rows = VGroup()
        for key, unit in metrics:
            ft, llm = n["fine_tuned"][key], n["zero_shot_llm"][key]
            row = VGroup(T(key, 0.5, GREY_A, bold=True),
                         T(f"fine-tuned: {ft}{unit}", 0.46, PUR, bold=True),
                         T(f"LLM: {llm}{unit}", 0.46, BLUE_N, bold=True)).arrange(RIGHT, buff=0.8)
            rows.add(row)
        rows.arrange(DOWN, buff=0.6, aligned_edge=LEFT).move_to(0.2 * DOWN)
        for r in rows:
            self.play(FadeIn(r[0]), Write(r[1]), Write(r[2]), run_time=1.0)
        self.wait(1.5)


class Evals(Scene):
    def construct(self):
        n = load_numbers()["evals"]
        ttl = title("What you show the client")
        self.play(Write(ttl), run_time=0.7)
        items = [("right category", n["intent_accuracy"], "%"), ("right tool chosen", n["tool_accuracy"], "%"),
                 ("facts found for the answer", n["facts_found"], "%")]
        rows = VGroup()
        decs = []
        for lbl, val, unit in items:
            d = DecimalNumber(0, num_decimal_places=0, font_size=60).set_color(GRN)
            u = T(unit, 0.6, GRN, bold=True)
            rows.add(VGroup(T(lbl, 0.5, GREY_A), VGroup(d, u).arrange(RIGHT, buff=0.08)).arrange(RIGHT, buff=0.6))
            decs.append((d, val))
        extra = T(f'{n["emails"]} unseen emails · about {n["seconds_per_email"]} s per email before the LLM writes', 0.42, BLUE_N, bold=True)
        rows.add(extra)
        rows.arrange(DOWN, buff=0.5, aligned_edge=LEFT).move_to(0.2 * DOWN)
        self.play(LaggedStart(*[FadeIn(r) for r in rows], lag_ratio=0.2), run_time=1.2)
        self.play(*[ChangeDecimalToValue(d, v) for d, v in decs], run_time=1.6)
        self.wait(1.5)


# ------------------------------------------------------------ 10b EC2
class EC2(Scene):
    def construct(self):
        ttl = title("Ship it to AWS EC2")
        self.play(Write(ttl), run_time=0.7)
        push = box("push to main", BLUE_N, 2.2, 0.7, 0.34).move_to(5.4 * LEFT + 1.4 * UP)
        gate = box("tests + eval gate", YEL, 2.6, 0.7, 0.32).move_to(2.2 * LEFT + 1.4 * UP)
        ssh = box("GitHub Actions", BLUE_N, 2.4, 0.9, 0.34, sub="SSH with secrets").move_to(1.2 * RIGHT + 1.4 * UP)
        ec2 = RoundedRectangle(width=4.6, height=3.0, corner_radius=0.2).set_stroke(GRN, 3).set_fill(GRN, 0.06).move_to(4.4 * RIGHT + 1.0 * DOWN)
        ec2_l = T("EC2 server", 0.4, GRN, bold=True).next_to(ec2.get_top(), DOWN, buff=0.15)
        inner = VGroup(box("app :8501", BLUE_N, 1.8, 0.6, 0.3), box("Postgres", BLUE_N, 1.8, 0.6, 0.3)).arrange(RIGHT, buff=0.25).move_to(ec2.get_center() + 0.1 * DOWN)
        cmd = T("docker compose up", 0.3, GREY_A).next_to(inner, DOWN, buff=0.25)
        a = [edge_arrow(push.get_right(), gate.get_left()), edge_arrow(gate.get_right(), ssh.get_left()), edge_arrow(ssh.get_bottom(), ec2.get_top() + 1.2 * LEFT)]
        self.play(LaggedStart(*[FadeIn(x, shift=0.15 * RIGHT) for x in (push, gate, ssh)], lag_ratio=0.25), GrowArrow(a[0]), GrowArrow(a[1]), run_time=1.3)
        self.play(flow(a[0]), flow(a[1]), run_time=0.8)
        self.play(ShowCreation(ec2), FadeIn(ec2_l), GrowArrow(a[2]), run_time=1.0)
        self.play(flow(a[2], GRN), LaggedStart(*[FadeIn(x, scale=0.9) for x in inner], lag_ratio=0.2), Write(cmd), run_time=1.2)
        secrets = VGroup(chip("EC2_HOST", PUR), chip("EC2_USER", PUR), chip("EC2_SSH_KEY", PUR)).arrange(RIGHT, buff=0.2).move_to(2.6 * LEFT + 0.25 * UP)
        sec_l = T("GitHub secrets, never in the code", 0.3, PUR).next_to(secrets, DOWN, buff=0.15)
        self.play(LaggedStart(*[FadeIn(s, shift=0.1 * UP) for s in secrets], lag_ratio=0.2), FadeIn(sec_l), run_time=1.0)
        you = box("your IP", EDGE, 1.6, 0.55, 0.3).move_to(5.3 * LEFT + 2.2 * DOWN)
        office = box("client office", EDGE, 2.0, 0.55, 0.3).move_to(5.3 * LEFT + 3.0 * DOWN)
        r1 = edge_arrow(you.get_right(), ec2.get_left() + 0.5 * UP, EDGE)
        r2 = edge_arrow(office.get_right(), ec2.get_left() + 0.3 * DOWN, EDGE)
        l1 = T("SSH :22", 0.3, GREY_A).move_to(r1.get_center() + 0.32 * UP)
        l2 = T("app :8501", 0.3, GREY_A).move_to(r2.get_center() + 0.32 * DOWN)
        closed = chip("everything else closed", RED_E).next_to(ec2, DOWN, buff=0.15)
        self.play(FadeIn(you), FadeIn(office), GrowArrow(r1), GrowArrow(r2), FadeIn(l1), FadeIn(l2), run_time=1.0)
        self.play(FadeIn(closed, scale=1.15), run_time=0.6)
        self.wait(1.2)
