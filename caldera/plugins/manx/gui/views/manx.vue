<script setup>
import { inject, ref, onMounted, computed } from "vue";
import { storeToRefs } from "pinia";

const $api = inject("$api");

onMounted(async () => {});

</script>

<script>
import { toast } from "bulma-toast";
import { useCoreStore } from "@/stores/coreStore";
import { mapState } from "pinia";
import { loadCommand, setCommand } from '@/../../manx/static/js/terminal.js'

export default {
    inject: ["$api"],
    data() {
        return {
            DEFAULT_EXECUTORS: ['sh'],
            DEFAULT_PLATFORM: 'darwin',

            sessions: [],
            tactics: [],
            techniques: [],
            procedures: [],
            selectedSessionID: '',
            selectedTacticName: '',
            selectedTechniqueID: '',
            selectedProcedureID: '',
            terminalCommand: '',

            get sessionIDs() {
                return this.sessions ? this.sessions.flatMap((s) => s.id) : [];
            },

            get selectedSession() {
                return this.sessions ? (this.sessions.find((s) => s.id.toString() === this.selectedSessionID.toString())) : null;
            },
        }
    },
    mounted() {
        this.initPage();
    },
    computed: {
        ...mapState(useCoreStore, ["mainConfig"]),
    },
    watch: {
        selectedSessionID() {
            this.resetFields();
        },
    },
  methods: {
    async initPage() {
        loadCommand(this.$api);

        this.refreshManx();
        setInterval(async () => {
            this.refreshManx();
        }, "3000");
    },

    refreshManx() {
        this.$api.get('/plugin/manx/sessions').then((sessions) => {
            // Join new manx agents in array, and assign default platform and executors if DNE
            sessions = sessions.data.sessions;
            this.sessions = this.sessions.concat(sessions.map((s) => ({ ...s, platform: s.platform || this.DEFAULT_PLATFORM, executors: s.executors || [this.DEFAULT_EXECUTORS] })).filter((s) => !this.sessionIDs.includes(s.id)));
        }).catch((error) => {
            toast({message: "Error refreshing manx", type: "is-danger", dismissible: true, pauseOnHover: true, duration: 2000})
            console.error(error);
        });
    },

    resetFields() {
        this.selectedTacticName = '';
        this.selectedTechniqueID = '';
        this.selectedProcedureID = '';
    },

    getTactics() {
        const getUniqueAbilities = (self, data) => {
            if (data.abilities) {
                const seen = [];
                self.tactics = data.abilities.filter((a) => {
                    if (!seen.includes(a.tactic)) {
                        seen.push(a.tactic);
                        return true;
                    }
                    return false;
                });
            }
        };
        this.$api.post("/plugin/manx/ability", { paw: this.selectedSession.info}).then((res) => {
            getUniqueAbilities(this, res.data);
        }).catch((error) => {
            toast({message: "Error getting tactics", type: "is-danger", dismissible: true, pauseOnHover: true, duration: 2000})
            console.error(error);
        })
    },

    getTechniques() {
        this.selectedTechniqueID = '';
        this.selectedProcedureID = '';

        let seenIDs = [];
        this.techniques = this.tactics.filter((a) => {
            if (a.tactic === this.selectedTacticName && !seenIDs.includes(a.technique_id)) {
                seenIDs.push(a.technique_id);
                return true;
            }
            return false;
        });
    },

    getProcedures() {
        this.selectedProcedureID = '';

        this.procedures = this.techniques.filter((t) => t.technique_id === this.selectedTechniqueID);
    },

    getProcedure() {
        const getCommands = (self, data) => {
            if (data && data.length > 0) {
                data.forEach((ability) => {
                    const executor = ability.executors.find((e) => e.platform === self.selectedSession.platform && e.name === self.selectedSession.executors[0]);
                    setCommand(executor ? executor.command : '');
                });
            } else {
                toast({message: "No ability available for this agents platform and executor combination", type: "is-warning", dismissible: true, pauseOnHover: true, duration: 2000})
            };
      }
      this.$api.post("/api/rest", {
          index: 'abilities',
          ability_id: this.selectedProcedureID
      }).then((res) => {
          getCommands(this, res.data);
      }).catch((error) => {
          toast({message: "Error getting abilities", type: "is-danger", dismissible: true, pauseOnHover: true, duration: 2000})
          console.error(error);
      })
    }
  }
}
</script>

<template lang="pug">
#manxPage(v-cloak)
  div(id="websocket-data" :data-websocket="mainConfig['app.contact.websocket']")
    h2 Manx
    p.has-text-weight-bold A coordinated access trojan (CAT)
    p
      | The Manx agent, written in GoLang, connects to the server over the TCP 
      i contact point
      | . This raw TCP socket connection allows Manx to keep a persistent connection between host-and-server. Bundled with Manx is a reverse-shell management tool, called the 
      i terminal
      | - below - which allows you to establish a local shell on an agent.
    p.has-text-weight-bold To deploy a Manx agent, go to the Agents tab.
  hr
  .is-flex.is-flex-direction-column
    h3 Terminal
    .is-flex.is-flex-direction-row.is-justify-content-space-around.mb-5
      .select.is-small
        select#session-id(v-model="selectedSessionID" @change="getTactics")
          option(value="" disabled selected) Select a session
          template(v-for="s in sessions" :key="s.id")
            option(:value="s.id" :data-paw="s.info" :data-platform="s.platform" :data-executor="s.executors ? s.executors[0] : 'sh'" v-text="s.id + ' - ' + s.info")
      .select.is-small
        select(v-model="selectedTacticName" id="tactic-filter" @change="getTechniques")
          option(value="" disabled selected) Select a tactic
          template(v-for="a in tactics" :key="a.ability_id")
            option(v-text="a.tactic")
      .select.is-small
        select(v-model="selectedTechniqueID" @change="getProcedures")
          option(value="" disabled selected) Select a technique
          template(v-for="t in techniques" :key="t.technique_id")
            option(:value="t.technique_id" v-text="t.technique_id + ' | ' + t.technique_name")
      .select.is-small
        select#procedure-filter(v-model="selectedProcedureID" @change="getProcedure")
          option(value="" disabled selected) Select a procedure
          template(v-for="p in procedures")
            option(v-text="p.name" :value="p.ability_id")
    input(style="visibility:hidden;position:absolute" id="xterminal-command" v-model="terminalCommand")
    div#xterminal
</template>

<style>
.terminal {
    border-radius: 10px;
    background-color: var(--primary-background);
}
.terminal p,h2 {
    color: white;
}
.terminal td {
    color: white;
}
.terminal pre {
    border: none;
    background-color: inherit;
    color: white;
    margin: 5px;
    height: 400px;
    width: 95%;
}
.ability-filter tr td {
    width: 22%;
}
/**
 * Copyright (c) 2014 The xterm.js authors. All rights reserved.
 * Copyright (c) 2012-2013, Christopher Jeffrey (MIT License)
 * https://github.com/chjj/term.js
 * @license MIT
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 *
 * Originally forked from (with the author's permission):
 *   Fabrice Bellard's javascript vt100 for jslinux:
 *   http://bellard.org/jslinux/
 *   Copyright (c) 2011 Fabrice Bellard
 *   The original design remains. The terminal itself
 *   has been extended to include xterm CSI codes, among
 *   other features.
 */

/**
 *  Default styles for xterm.js
 */

.xterm {
    font-feature-settings: "liga" 0;
    position: relative;
    user-select: none;
    -ms-user-select: none;
    -webkit-user-select: none;
}

.xterm.focus,
.xterm:focus {
    outline: none;
}

.xterm .xterm-helpers {
    position: absolute;
    top: 0;
    /**
     * The z-index of the helpers must be higher than the canvases in order for
     * IMEs to appear on top.
     */
    z-index: 5;
}

.xterm .xterm-helper-textarea {
    /*
     * HACK: to fix IE's blinking cursor
     * Move textarea out of the screen to the far left, so that the cursor is not visible.
     */
    position: absolute;
    opacity: 0;
    left: -9999em;
    top: 0;
    width: 0;
    height: 0;
    z-index: -5;
    /** Prevent wrapping so the IME appears against the textarea at the correct position */
    white-space: nowrap;
    overflow: hidden;
    resize: none;
}

.xterm .composition-view {
    /* TODO: Composition position got messed up somewhere */
    background: #000;
    color: #FFF;
    display: none;
    position: absolute;
    white-space: nowrap;
    z-index: 1;
}

.xterm .composition-view.active {
    display: block;
}

.xterm .xterm-viewport {
    /* On OS X this is required in order for the scroll bar to appear fully opaque */
    background-color: #000;
    overflow-y: scroll;
    cursor: default;
    position: absolute;
    right: 0;
    left: 0;
    top: 0;
    bottom: 0;
}

.xterm .xterm-screen {
    position: relative;
}

.xterm .xterm-screen canvas {
    position: absolute;
    left: 0;
    top: 0;
    padding: 12px 10px;
}

.xterm .xterm-scroll-area {
    visibility: hidden;
}

.xterm-char-measure-element {
    display: inline-block;
    visibility: hidden;
    position: absolute;
    top: 0;
    left: -9999em;
    line-height: normal;
}

.xterm {
    cursor: text;
}

.xterm.enable-mouse-events {
    /* When mouse events are enabled (eg. tmux), revert to the standard pointer cursor */
    cursor: default;
}

.xterm.xterm-cursor-pointer {
    cursor: pointer;
}

.xterm.column-select.focus {
    /* Column selection mode */
    cursor: crosshair;
}

.xterm .xterm-accessibility,
.xterm .xterm-message {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    right: 0;
    z-index: 10;
    color: transparent;
}

.xterm .live-region {
    position: absolute;
    left: -9999px;
    width: 1px;
    height: 1px;
    overflow: hidden;
}

.xterm-dim {
    opacity: 0.5;
}

.xterm-underline {
    text-decoration: underline;
}
</style>
