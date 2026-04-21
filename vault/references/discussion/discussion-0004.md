---
title: Replace categorical IDS relations with constraint-based scene graph; IDS as bootstrap not atomic
created: 2026-04-21
tags: [topic/chinese-font, topic/scene-graph, topic/constraints, topic/ids, type/ai-thread]
source: ai-thread
branch-from: "[[discussion-0003]]"
seq: 4
---

"structural relation: left_right, top_bottom, enclose, overlay, surround, grid, single"
I would like to enhance the concpet left_right, top_bottom.
This relationship to define top, bottom, left, right, is actually limited. And if we are going to create our own symbols(looks like Chinese but not actually Chinese nor Korean nor Japanese) this structural relation will be limited. It is better to go as normal scene graph does
Show more

Thought for 7s
Yes — I agree.

left_right and top_bottom are useful as legacy layout tags, but they are too tied to existing CJK decomposition habits. If you want a system that can also produce new pseudo-logographic symbols, then those labels become restrictive because they assume a small fixed grammar of arrangements.

A better model is:

not “this glyph is left-right”
but
“this glyph is a scene graph of spatial objects with transforms, anchors, and constraints.”

So I would move from a categorical relation model to a geometric constraint model.

Instead of this:

{
  "type": "left_right",
  "children": ["A", "B"]
}
use something closer to:

{
  "type": "group",
  "children": [
    {
      "id": "A",
      "transform": {
        "translate": [120, 180],
        "scale": [0.42, 0.88],
        "rotate": 0.0
      },
      "anchors": {
        "center": [0.5, 0.5],
        "right_mid": [1.0, 0.5]
      }
    },
    {
      "id": "B",
      "transform": {
        "translate": [540, 160],
        "scale": [0.46, 0.90],
        "rotate": -0.06
      },
      "anchors": {
        "center": [0.5, 0.5],
        "left_mid": [0.0, 0.5]
      }
    }
  ],
  "constraints": [
    {
      "kind": "anchor_distance",
      "from": "A.right_mid",
      "to": "B.left_mid",
      "value": 24
    },
    {
      "kind": "align_y",
      "targets": ["A.center", "B.center"]
    }
  ]
}
That gives you a normal scene-graph feel:
each node has geometry, transform, parent-child nesting, and optional constraints.

So I would replace the old relation vocabulary with three layers.

1. Topology layer
This answers: what belongs to what?

group

component

stroke

contour

decoration

mask

attachment

guide

This is the actual scene graph.

2. Geometry layer
This answers: where is it and how is it deformed?

Each node gets:

local coordinate system

transform

bbox

pivot

anchors

optional warp field

This is much more general than left/right/top/bottom.

3. Constraint layer
This answers: how should objects relate?

Instead of hardcoding left_right, define reusable constraints such as:

align x / align y

attach anchor to anchor

keep inside

surround

avoid overlap

preserve gap

tangent

center on path

radial array

mirror

repeat

distribute along curve

stack by priority

Now left_right becomes just a preset:

{
  "preset": "left_right",
  "expands_to": [
    {"kind": "align_y", "targets": ["A.center", "B.center"]},
    {"kind": "order_x", "before": "A", "after": "B"},
    {"kind": "anchor_distance", "from": "A.right_mid", "to": "B.left_mid", "value": 20}
  ]
}
That is the key shift:
left_right should not be a primitive.
It should be a macro built on general constraints.

That way you get both:

compatibility with traditional CJK structures

freedom for invented symbols

For new glyphs, this matters because many interesting arrangements are not classical IDS-like relations at all. You may want:

diagonal binding

spiral packing

one component piercing another

orbiting marks

concentric nesting

asymmetric balance

partial overlap

repeated shards around a core

calligraphic appendages growing from a skeleton

Those are much easier to express in a general scene graph than in a fixed relation enum.

So I would revise the node model to something like this:

{
  "id": "node_12",
  "kind": "component",
  "parent": "group_3",
  "geometry_ref": "comp_water_variant_b",
  "transform": {
    "translate": [312, 188],
    "scale": [0.62, 0.84],
    "rotate": -0.08,
    "shear": [0.03, 0.0]
  },
  "anchors": {
    "entry": [0.1, 0.5],
    "exit": [0.92, 0.47],
    "top": [0.5, 0.0],
    "bottom": [0.5, 1.0]
  },
  "constraints": [
    {"kind": "inside", "target": "frame_main"},
    {"kind": "avoid_overlap", "target": "node_13", "padding": 12},
    {"kind": "attach", "from": "exit", "to": "node_13.entry"}
  ],
  "style_slots": {
    "stroke_family": "ink_brush_02",
    "texture_zone": "edge_rough"
  }
}
This has a few big advantages.

First, it separates structure from interpretation.
A node is just a placed object. Whether a human later interprets that as “left radical” or “top enclosure” is secondary.

Second, it lets you support procedural generation much more naturally.
A generator can mutate:

transforms

anchors

constraints

child counts

symmetry rules
without needing to invent new enum labels every time.

Third, it works better with ComfyUI separation.
Your reconstruction engine outputs:

geometry

masks

depth/layer maps

adjacency maps

skeletons

ComfyUI then styles those outputs, without caring whether the original relation was “left_right” or “spiral_attach.”

So my recommendation is:

Keep the classical relations only as high-level conveniences for parsing real CJK characters, but make the true core model:

Scene Graph + Anchors + Constraints + Transforms

Concretely, I would define primitives like:

GroupNode

ComponentNode

StrokeNode

MaskNode

GuideNode

and relation/constraint primitives like:

attach

align

contain

overlap

avoid

mirror

repeat

project

distribute

order

blend

Then left_right, top_bottom, enclose, and friends become optional presets, not the ontology.

That is a much better foundation if the goal is not only to model Chinese characters, but to create a general logographic symbol construction system.

The cleanest phrase for it would be:

CJK decomposition grammar is one frontend.
Constraint-based glyph scene graph is the backend.

If you want, I can draft a compact formal spec for this backend next, with node types and constraint types written like an actual schema.


Speaking of "classical IDS-like relations", I think IDS is usually not the most atomic representation of components. That means we should based on it and extend to further decompose or replace some component.
Since we are making it glyph scene graph, tree concept(if not graph) should be very important. We attempt to reconstruct a symbol by using components to reduce the size.
Show more

Thought for 5s
Yes — that is the right refinement.

IDS is useful, but mostly as a coarse structural prior, not as the final atomic decomposition.

What IDS gives you well:

a first-pass hierarchical split

a human-readable structural scaffold

compatibility with existing CJK decomposition resources

What IDS does not give you well:

the truly smallest reusable parts

style-sensitive substitutions

context-specific variants

arbitrary invented-symbol structure

So I would treat IDS as a bootstrap tree, then allow your system to refine nodes further.

Better model
Think of decomposition in three layers:

1. Structural tree
This is the high-level parse, often IDS-like.

Example:

root

left part

right part

Useful for:

initial layout

broad composition

matching existing Hanzi data

2. Component refinement tree
Each structural node may be decomposed again into smaller reusable units.

Example:

言 is not necessarily atomic

it may decompose into top cap, middle bars, vertical stem, bottom mouth-like part

in some styles, those are better style units than the whole 言

So a node can be:

kept as one component

decomposed further

replaced by a variant-specific sub-tree

This is the layer that really helps reduce total storage.

3. Instance tree
This is the actual glyph build tree for one rendered symbol.

It references:

reusable component prototypes

transforms

constraints

style bindings

So the same prototype can appear many times in many symbols.

Important idea: atomic is not absolute
A component is not “atomic” in a universal sense.

Atomic depends on your goal:

for dictionary decomposition, a radical may be atomic

for compression, a smaller recurring shape may be atomic

for styling, the atomic unit may be a stroke cluster

for brush simulation, the atomic unit may be a single stroke or even stroke segment

So your system should not force one universal atom.
It should support multi-resolution decomposition.

A good rule is:

A node is atomic only relative to the current operation.

For example:

layout stage: keep larger components

style stage: split into finer style-bearing units

export stage: maybe flatten again

Tree is very important, but with one twist
I agree the tree concept should be central for reconstruction.

Why tree matters:

composition is hierarchical

transforms propagate naturally

layout is easier

refinement is local

partial replacement is clean

But for storage efficiency, the full system is better as:

build-time representation: tree

library/prototype representation: graph or DAG

In other words:

each glyph instance is reconstructed as a tree

the component library is shared as a graph of reusable prototypes

That gives you both:

simple reconstruction logic

compact storage

So you might say:

Glyph assembly is tree-based.
Component reuse is graph-based.

That is probably the cleanest formulation.

Recommended node behavior
Each node in the tree should support three actions:

keep

use this node as-is

refine

decompose this node into child nodes

replace

swap this node for another equivalent or style-specific variant

That makes the system flexible.

Example:

{
  "node_id": "comp_A",
  "prototype": "言",
  "mode": "refine",
  "children": [
    {"prototype": "言_top_cap"},
    {"prototype": "言_mid_bar_1"},
    {"prototype": "言_mid_bar_2"},
    {"prototype": "言_stem"},
    {"prototype": "言_bottom_box"}
  ]
}
Or in another style:

{
  "node_id": "comp_A",
  "prototype": "言_cursive_variant",
  "mode": "keep"
}
So the same symbolic node can be expanded differently depending on style or efficiency needs.

Best architecture for your goal
I would define the system like this:

A. Prototype library
Stores reusable shapes:

components

subcomponents

strokes

optional stroke segments

Each prototype has:

geometry

anchors

semantic tags

refinement rules

replacement rules

B. Decomposition grammar
Starts from IDS-like structure, but extends it.

Rules can say:

this node may refine into these children

this component may be replaced in narrow-left context

this component may compress when enclosed

this prototype has style-dependent alternates

C. Glyph build tree
For one symbol:

choose a root

refine recursively

place children

apply transforms

bind styles

render

This is your actual glyph scene tree.

Compression insight
Your intuition about reducing size is exactly right.

If you store every symbol independently, complexity scales with symbol count.

If you store:

a reusable prototype bank

refinement rules

composition trees

then complexity scales more like:

number of unique reusable parts

number of layout/refinement rules

number of symbol definitions

That is far more manageable than storing 10,000 full glyphs.

Especially for pseudo-CJK symbol creation, this is powerful because you can generate many new symbols by:

recombining existing prototypes

refining at different levels

swapping variants

Practical formulation
I would describe your core model as:

A glyph is a hierarchical composition tree of reusable prototypes, where each node may be refined, replaced, transformed, and styled.

That is stronger than plain IDS.

And I would describe IDS as:

an initial parse layer, not the final atomic layer.

My strongest recommendation
Make each node carry both:

a semantic identity

a refinement option

For example:

{
  "prototype_id": "component_speech",
  "semantic_role": "speech_family",
  "refinable": true,
  "refinement_set": ["speech_full", "speech_split_5", "speech_cursive"]
}
That way your system can decide later whether to keep it coarse or split it finer.

So yes:

IDS is not atomic enough

tree structure should be central

size reduction comes from reusable components

but the best version is recursive refinement on top of IDS, not IDS alone

The sentence I would use for the design doc is:

IDS provides the initial hierarchical scaffold; the glyph scene tree refines that scaffold into reusable atomic prototypes for reconstruction and style control.
