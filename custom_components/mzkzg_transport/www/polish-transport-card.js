//#region node_modules/@lit/reactive-element/css-tag.js
var e = globalThis, t = e.ShadowRoot && (e.ShadyCSS === void 0 || e.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, n = Symbol(), r = /* @__PURE__ */ new WeakMap(), i = class {
	constructor(e, t, r) {
		if (this._$cssResult$ = !0, r !== n) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
		this.cssText = e, this.t = t;
	}
	get styleSheet() {
		let e = this.o, n = this.t;
		if (t && e === void 0) {
			let t = n !== void 0 && n.length === 1;
			t && (e = r.get(n)), e === void 0 && ((this.o = e = new CSSStyleSheet()).replaceSync(this.cssText), t && r.set(n, e));
		}
		return e;
	}
	toString() {
		return this.cssText;
	}
}, a = (e) => new i(typeof e == "string" ? e : e + "", void 0, n), o = (e, ...t) => new i(e.length === 1 ? e[0] : t.reduce((t, n, r) => t + ((e) => {
	if (!0 === e._$cssResult$) return e.cssText;
	if (typeof e == "number") return e;
	throw Error("Value passed to 'css' function must be a 'css' function result: " + e + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
})(n) + e[r + 1], e[0]), e, n), s = (n, r) => {
	if (t) n.adoptedStyleSheets = r.map((e) => e instanceof CSSStyleSheet ? e : e.styleSheet);
	else for (let t of r) {
		let r = document.createElement("style"), i = e.litNonce;
		i !== void 0 && r.setAttribute("nonce", i), r.textContent = t.cssText, n.appendChild(r);
	}
}, c = t ? (e) => e : (e) => e instanceof CSSStyleSheet ? ((e) => {
	let t = "";
	for (let n of e.cssRules) t += n.cssText;
	return a(t);
})(e) : e, { is: l, defineProperty: u, getOwnPropertyDescriptor: d, getOwnPropertyNames: f, getOwnPropertySymbols: p, getPrototypeOf: ee } = Object, m = globalThis, h = m.trustedTypes, g = h ? h.emptyScript : "", _ = m.reactiveElementPolyfillSupport, v = (e, t) => e, y = {
	toAttribute(e, t) {
		switch (t) {
			case Boolean:
				e = e ? g : null;
				break;
			case Object:
			case Array: e = e == null ? e : JSON.stringify(e);
		}
		return e;
	},
	fromAttribute(e, t) {
		let n = e;
		switch (t) {
			case Boolean:
				n = e !== null;
				break;
			case Number:
				n = e === null ? null : Number(e);
				break;
			case Object:
			case Array: try {
				n = JSON.parse(e);
			} catch {
				n = null;
			}
		}
		return n;
	}
}, te = (e, t) => !l(e, t), ne = {
	attribute: !0,
	type: String,
	converter: y,
	reflect: !1,
	useDefault: !1,
	hasChanged: te
};
Symbol.metadata ??= Symbol("metadata"), m.litPropertyMetadata ??= /* @__PURE__ */ new WeakMap();
var b = class extends HTMLElement {
	static addInitializer(e) {
		this._$Ei(), (this.l ??= []).push(e);
	}
	static get observedAttributes() {
		return this.finalize(), this._$Eh && [...this._$Eh.keys()];
	}
	static createProperty(e, t = ne) {
		if (t.state && (t.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(e) && ((t = Object.create(t)).wrapped = !0), this.elementProperties.set(e, t), !t.noAccessor) {
			let n = Symbol(), r = this.getPropertyDescriptor(e, n, t);
			r !== void 0 && u(this.prototype, e, r);
		}
	}
	static getPropertyDescriptor(e, t, n) {
		let { get: r, set: i } = d(this.prototype, e) ?? {
			get() {
				return this[t];
			},
			set(e) {
				this[t] = e;
			}
		};
		return {
			get: r,
			set(t) {
				let a = r?.call(this);
				i?.call(this, t), this.requestUpdate(e, a, n);
			},
			configurable: !0,
			enumerable: !0
		};
	}
	static getPropertyOptions(e) {
		return this.elementProperties.get(e) ?? ne;
	}
	static _$Ei() {
		if (this.hasOwnProperty(v("elementProperties"))) return;
		let e = ee(this);
		e.finalize(), e.l !== void 0 && (this.l = [...e.l]), this.elementProperties = new Map(e.elementProperties);
	}
	static finalize() {
		if (this.hasOwnProperty(v("finalized"))) return;
		if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(v("properties"))) {
			let e = this.properties, t = [...f(e), ...p(e)];
			for (let n of t) this.createProperty(n, e[n]);
		}
		let e = this[Symbol.metadata];
		if (e !== null) {
			let t = litPropertyMetadata.get(e);
			if (t !== void 0) for (let [e, n] of t) this.elementProperties.set(e, n);
		}
		this._$Eh = /* @__PURE__ */ new Map();
		for (let [e, t] of this.elementProperties) {
			let n = this._$Eu(e, t);
			n !== void 0 && this._$Eh.set(n, e);
		}
		this.elementStyles = this.finalizeStyles(this.styles);
	}
	static finalizeStyles(e) {
		let t = [];
		if (Array.isArray(e)) {
			let n = new Set(e.flat(1 / 0).reverse());
			for (let e of n) t.unshift(c(e));
		} else e !== void 0 && t.push(c(e));
		return t;
	}
	static _$Eu(e, t) {
		let n = t.attribute;
		return !1 === n ? void 0 : typeof n == "string" ? n : typeof e == "string" ? e.toLowerCase() : void 0;
	}
	constructor() {
		super(), this._$Ep = void 0, this.isUpdatePending = !1, this.hasUpdated = !1, this._$Em = null, this._$Ev();
	}
	_$Ev() {
		this._$ES = new Promise((e) => this.enableUpdating = e), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), this.constructor.l?.forEach((e) => e(this));
	}
	addController(e) {
		(this._$EO ??= /* @__PURE__ */ new Set()).add(e), this.renderRoot !== void 0 && this.isConnected && e.hostConnected?.();
	}
	removeController(e) {
		this._$EO?.delete(e);
	}
	_$E_() {
		let e = /* @__PURE__ */ new Map(), t = this.constructor.elementProperties;
		for (let n of t.keys()) this.hasOwnProperty(n) && (e.set(n, this[n]), delete this[n]);
		e.size > 0 && (this._$Ep = e);
	}
	createRenderRoot() {
		let e = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
		return s(e, this.constructor.elementStyles), e;
	}
	connectedCallback() {
		this.renderRoot ??= this.createRenderRoot(), this.enableUpdating(!0), this._$EO?.forEach((e) => e.hostConnected?.());
	}
	enableUpdating(e) {}
	disconnectedCallback() {
		this._$EO?.forEach((e) => e.hostDisconnected?.());
	}
	attributeChangedCallback(e, t, n) {
		this._$AK(e, n);
	}
	_$ET(e, t) {
		let n = this.constructor.elementProperties.get(e), r = this.constructor._$Eu(e, n);
		if (r !== void 0 && !0 === n.reflect) {
			let i = (n.converter?.toAttribute === void 0 ? y : n.converter).toAttribute(t, n.type);
			this._$Em = e, i == null ? this.removeAttribute(r) : this.setAttribute(r, i), this._$Em = null;
		}
	}
	_$AK(e, t) {
		let n = this.constructor, r = n._$Eh.get(e);
		if (r !== void 0 && this._$Em !== r) {
			let e = n.getPropertyOptions(r), i = typeof e.converter == "function" ? { fromAttribute: e.converter } : e.converter?.fromAttribute === void 0 ? y : e.converter;
			this._$Em = r;
			let a = i.fromAttribute(t, e.type);
			this[r] = a ?? this._$Ej?.get(r) ?? a, this._$Em = null;
		}
	}
	requestUpdate(e, t, n, r = !1, i) {
		if (e !== void 0) {
			let a = this.constructor;
			if (!1 === r && (i = this[e]), n ??= a.getPropertyOptions(e), !((n.hasChanged ?? te)(i, t) || n.useDefault && n.reflect && i === this._$Ej?.get(e) && !this.hasAttribute(a._$Eu(e, n)))) return;
			this.C(e, t, n);
		}
		!1 === this.isUpdatePending && (this._$ES = this._$EP());
	}
	C(e, t, { useDefault: n, reflect: r, wrapped: i }, a) {
		n && !(this._$Ej ??= /* @__PURE__ */ new Map()).has(e) && (this._$Ej.set(e, a ?? t ?? this[e]), !0 !== i || a !== void 0) || (this._$AL.has(e) || (this.hasUpdated || n || (t = void 0), this._$AL.set(e, t)), !0 === r && this._$Em !== e && (this._$Eq ??= /* @__PURE__ */ new Set()).add(e));
	}
	async _$EP() {
		this.isUpdatePending = !0;
		try {
			await this._$ES;
		} catch (e) {
			Promise.reject(e);
		}
		let e = this.scheduleUpdate();
		return e != null && await e, !this.isUpdatePending;
	}
	scheduleUpdate() {
		return this.performUpdate();
	}
	performUpdate() {
		if (!this.isUpdatePending) return;
		if (!this.hasUpdated) {
			if (this.renderRoot ??= this.createRenderRoot(), this._$Ep) {
				for (let [e, t] of this._$Ep) this[e] = t;
				this._$Ep = void 0;
			}
			let e = this.constructor.elementProperties;
			if (e.size > 0) for (let [t, n] of e) {
				let { wrapped: e } = n, r = this[t];
				!0 !== e || this._$AL.has(t) || r === void 0 || this.C(t, void 0, n, r);
			}
		}
		let e = !1, t = this._$AL;
		try {
			e = this.shouldUpdate(t), e ? (this.willUpdate(t), this._$EO?.forEach((e) => e.hostUpdate?.()), this.update(t)) : this._$EM();
		} catch (t) {
			throw e = !1, this._$EM(), t;
		}
		e && this._$AE(t);
	}
	willUpdate(e) {}
	_$AE(e) {
		this._$EO?.forEach((e) => e.hostUpdated?.()), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(e)), this.updated(e);
	}
	_$EM() {
		this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = !1;
	}
	get updateComplete() {
		return this.getUpdateComplete();
	}
	getUpdateComplete() {
		return this._$ES;
	}
	shouldUpdate(e) {
		return !0;
	}
	update(e) {
		this._$Eq &&= this._$Eq.forEach((e) => this._$ET(e, this[e])), this._$EM();
	}
	updated(e) {}
	firstUpdated(e) {}
};
b.elementStyles = [], b.shadowRootOptions = { mode: "open" }, b[v("elementProperties")] = /* @__PURE__ */ new Map(), b[v("finalized")] = /* @__PURE__ */ new Map(), _?.({ ReactiveElement: b }), (m.reactiveElementVersions ??= []).push("2.1.2");
//#endregion
//#region node_modules/lit-html/lit-html.js
var re = globalThis, ie = (e) => e, x = re.trustedTypes, ae = x ? x.createPolicy("lit-html", { createHTML: (e) => e }) : void 0, oe = "$lit$", S = `lit$${Math.random().toFixed(9).slice(2)}$`, se = "?" + S, ce = `<${se}>`, C = document, w = () => C.createComment(""), T = (e) => e === null || typeof e != "object" && typeof e != "function", E = Array.isArray, le = (e) => E(e) || typeof e?.[Symbol.iterator] == "function", D = "[ 	\n\f\r]", O = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, ue = /-->/g, de = />/g, k = RegExp(`>|${D}(?:([^\\s"'>=/]+)(${D}*=${D}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`, "g"), fe = /'/g, pe = /"/g, me = /^(?:script|style|textarea|title)$/i, he = (e) => (t, ...n) => ({
	_$litType$: e,
	strings: t,
	values: n
}), A = he(1), j = he(2), M = Symbol.for("lit-noChange"), N = Symbol.for("lit-nothing"), ge = /* @__PURE__ */ new WeakMap(), P = C.createTreeWalker(C, 129);
function _e(e, t) {
	if (!E(e) || !e.hasOwnProperty("raw")) throw Error("invalid template strings array");
	return ae === void 0 ? t : ae.createHTML(t);
}
var ve = (e, t) => {
	let n = e.length - 1, r = [], i, a = t === 2 ? "<svg>" : t === 3 ? "<math>" : "", o = O;
	for (let t = 0; t < n; t++) {
		let n = e[t], s, c, l = -1, u = 0;
		for (; u < n.length && (o.lastIndex = u, c = o.exec(n), c !== null);) u = o.lastIndex, o === O ? c[1] === "!--" ? o = ue : c[1] === void 0 ? c[2] === void 0 ? c[3] !== void 0 && (o = k) : (me.test(c[2]) && (i = RegExp("</" + c[2], "g")), o = k) : o = de : o === k ? c[0] === ">" ? (o = i ?? O, l = -1) : c[1] === void 0 ? l = -2 : (l = o.lastIndex - c[2].length, s = c[1], o = c[3] === void 0 ? k : c[3] === "\"" ? pe : fe) : o === pe || o === fe ? o = k : o === ue || o === de ? o = O : (o = k, i = void 0);
		let d = o === k && e[t + 1].startsWith("/>") ? " " : "";
		a += o === O ? n + ce : l >= 0 ? (r.push(s), n.slice(0, l) + oe + n.slice(l) + S + d) : n + S + (l === -2 ? t : d);
	}
	return [_e(e, a + (e[n] || "<?>") + (t === 2 ? "</svg>" : t === 3 ? "</math>" : "")), r];
}, F = class e {
	constructor({ strings: t, _$litType$: n }, r) {
		let i;
		this.parts = [];
		let a = 0, o = 0, s = t.length - 1, c = this.parts, [l, u] = ve(t, n);
		if (this.el = e.createElement(l, r), P.currentNode = this.el.content, n === 2 || n === 3) {
			let e = this.el.content.firstChild;
			e.replaceWith(...e.childNodes);
		}
		for (; (i = P.nextNode()) !== null && c.length < s;) {
			if (i.nodeType === 1) {
				if (i.hasAttributes()) for (let e of i.getAttributeNames()) if (e.endsWith(oe)) {
					let t = u[o++], n = i.getAttribute(e).split(S), r = /([.?@])?(.*)/.exec(t);
					c.push({
						type: 1,
						index: a,
						name: r[2],
						strings: n,
						ctor: r[1] === "." ? be : r[1] === "?" ? xe : r[1] === "@" ? Se : R
					}), i.removeAttribute(e);
				} else e.startsWith(S) && (c.push({
					type: 6,
					index: a
				}), i.removeAttribute(e));
				if (me.test(i.tagName)) {
					let e = i.textContent.split(S), t = e.length - 1;
					if (t > 0) {
						i.textContent = x ? x.emptyScript : "";
						for (let n = 0; n < t; n++) i.append(e[n], w()), P.nextNode(), c.push({
							type: 2,
							index: ++a
						});
						i.append(e[t], w());
					}
				}
			} else if (i.nodeType === 8) {
				if (i.data === se) c.push({
					type: 2,
					index: a
				});
				else {
					let e = -1;
					for (; (e = i.data.indexOf(S, e + 1)) !== -1;) c.push({
						type: 7,
						index: a
					}), e += S.length - 1;
				}
			}
			a++;
		}
	}
	static createElement(e, t) {
		let n = C.createElement("template");
		return n.innerHTML = e, n;
	}
};
function I(e, t, n = e, r) {
	if (t === M) return t;
	let i = r === void 0 ? n._$Cl : n._$Co?.[r], a = T(t) ? void 0 : t._$litDirective$;
	return i?.constructor !== a && (i?._$AO?.(!1), a === void 0 ? i = void 0 : (i = new a(e), i._$AT(e, n, r)), r === void 0 ? n._$Cl = i : (n._$Co ??= [])[r] = i), i !== void 0 && (t = I(e, i._$AS(e, t.values), i, r)), t;
}
var ye = class {
	constructor(e, t) {
		this._$AV = [], this._$AN = void 0, this._$AD = e, this._$AM = t;
	}
	get parentNode() {
		return this._$AM.parentNode;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	u(e) {
		let { el: { content: t }, parts: n } = this._$AD, r = (e?.creationScope ?? C).importNode(t, !0);
		P.currentNode = r;
		let i = P.nextNode(), a = 0, o = 0, s = n[0];
		for (; s !== void 0;) {
			if (a === s.index) {
				let t;
				s.type === 2 ? t = new L(i, i.nextSibling, this, e) : s.type === 1 ? t = new s.ctor(i, s.name, s.strings, this, e) : s.type === 6 && (t = new Ce(i, this, e)), this._$AV.push(t), s = n[++o];
			}
			a !== s?.index && (i = P.nextNode(), a++);
		}
		return P.currentNode = C, r;
	}
	p(e) {
		let t = 0;
		for (let n of this._$AV) n !== void 0 && (n.strings === void 0 ? n._$AI(e[t]) : (n._$AI(e, n, t), t += n.strings.length - 2)), t++;
	}
}, L = class e {
	get _$AU() {
		return this._$AM?._$AU ?? this._$Cv;
	}
	constructor(e, t, n, r) {
		this.type = 2, this._$AH = N, this._$AN = void 0, this._$AA = e, this._$AB = t, this._$AM = n, this.options = r, this._$Cv = r?.isConnected ?? !0;
	}
	get parentNode() {
		let e = this._$AA.parentNode, t = this._$AM;
		return t !== void 0 && e?.nodeType === 11 && (e = t.parentNode), e;
	}
	get startNode() {
		return this._$AA;
	}
	get endNode() {
		return this._$AB;
	}
	_$AI(e, t = this) {
		e = I(this, e, t), T(e) ? e === N || e == null || e === "" ? (this._$AH !== N && this._$AR(), this._$AH = N) : e !== this._$AH && e !== M && this._(e) : e._$litType$ === void 0 ? e.nodeType === void 0 ? le(e) ? this.k(e) : this._(e) : this.T(e) : this.$(e);
	}
	O(e) {
		return this._$AA.parentNode.insertBefore(e, this._$AB);
	}
	T(e) {
		this._$AH !== e && (this._$AR(), this._$AH = this.O(e));
	}
	_(e) {
		this._$AH !== N && T(this._$AH) ? this._$AA.nextSibling.data = e : this.T(C.createTextNode(e)), this._$AH = e;
	}
	$(e) {
		let { values: t, _$litType$: n } = e, r = typeof n == "number" ? this._$AC(e) : (n.el === void 0 && (n.el = F.createElement(_e(n.h, n.h[0]), this.options)), n);
		if (this._$AH?._$AD === r) this._$AH.p(t);
		else {
			let e = new ye(r, this), n = e.u(this.options);
			e.p(t), this.T(n), this._$AH = e;
		}
	}
	_$AC(e) {
		let t = ge.get(e.strings);
		return t === void 0 && ge.set(e.strings, t = new F(e)), t;
	}
	k(t) {
		E(this._$AH) || (this._$AH = [], this._$AR());
		let n = this._$AH, r, i = 0;
		for (let a of t) i === n.length ? n.push(r = new e(this.O(w()), this.O(w()), this, this.options)) : r = n[i], r._$AI(a), i++;
		i < n.length && (this._$AR(r && r._$AB.nextSibling, i), n.length = i);
	}
	_$AR(e = this._$AA.nextSibling, t) {
		for (this._$AP?.(!1, !0, t); e !== this._$AB;) {
			let t = ie(e).nextSibling;
			ie(e).remove(), e = t;
		}
	}
	setConnected(e) {
		this._$AM === void 0 && (this._$Cv = e, this._$AP?.(e));
	}
}, R = class {
	get tagName() {
		return this.element.tagName;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	constructor(e, t, n, r, i) {
		this.type = 1, this._$AH = N, this._$AN = void 0, this.element = e, this.name = t, this._$AM = r, this.options = i, n.length > 2 || n[0] !== "" || n[1] !== "" ? (this._$AH = Array(n.length - 1).fill(/* @__PURE__ */ new String()), this.strings = n) : this._$AH = N;
	}
	_$AI(e, t = this, n, r) {
		let i = this.strings, a = !1;
		if (i === void 0) e = I(this, e, t, 0), a = !T(e) || e !== this._$AH && e !== M, a && (this._$AH = e);
		else {
			let r = e, o, s;
			for (e = i[0], o = 0; o < i.length - 1; o++) s = I(this, r[n + o], t, o), s === M && (s = this._$AH[o]), a ||= !T(s) || s !== this._$AH[o], s === N ? e = N : e !== N && (e += (s ?? "") + i[o + 1]), this._$AH[o] = s;
		}
		a && !r && this.j(e);
	}
	j(e) {
		e === N ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, e ?? "");
	}
}, be = class extends R {
	constructor() {
		super(...arguments), this.type = 3;
	}
	j(e) {
		this.element[this.name] = e === N ? void 0 : e;
	}
}, xe = class extends R {
	constructor() {
		super(...arguments), this.type = 4;
	}
	j(e) {
		this.element.toggleAttribute(this.name, !!e && e !== N);
	}
}, Se = class extends R {
	constructor(e, t, n, r, i) {
		super(e, t, n, r, i), this.type = 5;
	}
	_$AI(e, t = this) {
		if ((e = I(this, e, t, 0) ?? N) === M) return;
		let n = this._$AH, r = e === N && n !== N || e.capture !== n.capture || e.once !== n.once || e.passive !== n.passive, i = e !== N && (n === N || r);
		r && this.element.removeEventListener(this.name, this, n), i && this.element.addEventListener(this.name, this, e), this._$AH = e;
	}
	handleEvent(e) {
		typeof this._$AH == "function" ? this._$AH.call(this.options?.host ?? this.element, e) : this._$AH.handleEvent(e);
	}
}, Ce = class {
	constructor(e, t, n) {
		this.element = e, this.type = 6, this._$AN = void 0, this._$AM = t, this.options = n;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	_$AI(e) {
		I(this, e);
	}
}, we = re.litHtmlPolyfillSupport;
we?.(F, L), (re.litHtmlVersions ??= []).push("3.3.3");
var Te = (e, t, n) => {
	let r = n?.renderBefore ?? t, i = r._$litPart$;
	if (i === void 0) {
		let e = n?.renderBefore ?? null;
		r._$litPart$ = i = new L(t.insertBefore(w(), e), e, void 0, n ?? {});
	}
	return i._$AI(e), i;
}, z = globalThis, B = class extends b {
	constructor() {
		super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
	}
	createRenderRoot() {
		let e = super.createRenderRoot();
		return this.renderOptions.renderBefore ??= e.firstChild, e;
	}
	update(e) {
		let t = this.render();
		this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = Te(t, this.renderRoot, this.renderOptions);
	}
	connectedCallback() {
		super.connectedCallback(), this._$Do?.setConnected(!0);
	}
	disconnectedCallback() {
		super.disconnectedCallback(), this._$Do?.setConnected(!1);
	}
	render() {
		return M;
	}
};
B._$litElement$ = !0, B.finalized = !0, z.litElementHydrateSupport?.({ LitElement: B });
var Ee = z.litElementPolyfillSupport;
Ee?.({ LitElement: B }), (z.litElementVersions ??= []).push("4.2.2");
//#endregion
//#region src/utils.js
var De = "1.7.0", V = {
	pl: {
		no_entities: "Dodaj encje sensorów w konfiguracji",
		no_departures: "Brak nadchodzących odjazdów",
		unavailable: "Dane niedostępne — sprawdź połączenie",
		missing_entities: "Brak encji w HA — sprawdź konfigurację karty",
		plk_rate_limit: "Limit API wyczerpany — dane odświeżą się automatycznie",
		cancelled: "odwołany",
		track: "tor",
		min: "min",
		departing: "Odjeżdża",
		show_on_map: "Pokaż pojazd na mapie",
		editor_data: "Dane",
		editor_appearance: "Wygląd",
		editor_filtering: "Filtrowanie",
		editor_interactions: "Interakcje",
		editor_advanced: "Zaawansowane"
	},
	en: {
		no_entities: "Add sensor entities in configuration",
		no_departures: "No upcoming departures",
		unavailable: "Data unavailable — check connection",
		missing_entities: "Configured entities were not found in Home Assistant",
		plk_rate_limit: "API rate limit reached — data will refresh automatically",
		cancelled: "cancelled",
		track: "track",
		min: "min",
		departing: "Departing",
		show_on_map: "Show vehicle on map",
		editor_data: "Data",
		editor_appearance: "Appearance",
		editor_filtering: "Filtering",
		editor_interactions: "Interactions",
		editor_advanced: "Advanced"
	}
};
function H(e) {
	return (V[(document.documentElement.lang || navigator.language || "pl").slice(0, 2)] || V.pl)[e] || V.pl[e] || e;
}
function U(e) {
	return String(e ?? "").replace(/[&<>"']/g, (e) => ({
		"&": "&amp;",
		"<": "&lt;",
		">": "&gt;",
		"\"": "&quot;",
		"'": "&#39;"
	})[e]);
}
function W(e, t) {
	if (e == null || t == null || e === "" || t === "") return null;
	let n = Number(e), r = Number(t);
	return !Number.isFinite(n) || !Number.isFinite(r) || n < -90 || n > 90 || r < -180 || r > 180 ? null : [n, r];
}
function Oe(e) {
	if (!e) return null;
	let t;
	if (/^\d{1,2}:\d{2}/.test(e)) {
		let n = /* @__PURE__ */ new Date(), [r, i, a] = e.split(":").map(Number);
		t = new Date(n.getFullYear(), n.getMonth(), n.getDate(), r, i, a || 0), t - n < -36e5 && t.setDate(t.getDate() + 1);
	} else t = new Date(e);
	return isNaN(t.getTime()) ? null : Math.round((t - Date.now()) / 6e4);
}
function G(e) {
	return e ? /^\d{1,2}:\d{2}/.test(e) ? e.slice(0, 5) : new Date(e).toLocaleTimeString("pl-PL", {
		hour: "2-digit",
		minute: "2-digit"
	}) : "—";
}
function ke(e) {
	if (e === null || e < 0) return "";
	if (e === 0) return "&lt;1 min";
	if (e >= 60) {
		let t = Math.floor(e / 60), n = e % 60;
		return n ? `${t}h ${n}min` : `${t}h`;
	}
	return `${e} min`;
}
function K(e, t, n = null) {
	if (n) return n;
	let r = String(e || "");
	if (/^[Nn]/.test(r)) return "#1e293b";
	if (t === "zkm_gdynia") {
		let e = parseInt(r, 10);
		return !isNaN(e) && e >= 20 && e <= 29 ? "#0891b2" : "#ea580c";
	}
	if (t === "mzk_wejherowo") return "#478AC9";
	if (t === "plk_rail") {
		let e = r.toUpperCase();
		return e.startsWith("S") && e.length <= 3 ? "#1a3668" : e === "EIP" || e === "EIC" ? "#1a1a4e" : e === "IC" ? "#f57c00" : e === "TLK" ? "#7b1fa2" : "#d32f2f";
	}
	if (t === "ztm_gdansk") {
		let e = parseInt(r, 10);
		return !isNaN(e) && e < 100 ? e >= 90 ? "#8b5cf6" : e >= 60 && e < 70 ? "#f59e0b" : e <= 15 ? "#0369a1" : "#DA2128" : "#DA2128";
	}
	if (t === "gtfsrt_poznan") {
		let e = parseInt(r, 10);
		return !isNaN(e) && e <= 18 ? "#006b3f" : !isNaN(e) && e >= 100 ? "#15803d" : "#2d8a4e";
	}
	if (t === "gtfsrt_lublin") {
		let e = parseInt(r, 10);
		return !isNaN(e) && e <= 10 ? "#1565c0" : !isNaN(e) && e >= 150 ? "#0d47a1" : "#1976d2";
	}
	if (t === "gtfsrt_kielce") {
		let e = parseInt(r, 10);
		return !isNaN(e) && e <= 5 ? "#004d40" : "#00796b";
	}
	if (t === "gtfsrt_czestochowa") {
		let e = parseInt(r, 10);
		return !isNaN(e) && e <= 15 ? "#b71c1c" : "#d32f2f";
	}
	if (t === "gtfsrt_elblag") {
		let e = parseInt(r, 10);
		return !isNaN(e) && e <= 5 ? "#01579b" : "#0277bd";
	}
	if (t === "gtfsrt_gorzow") {
		let e = parseInt(r, 10);
		return !isNaN(e) && e <= 3 ? "#1b5e20" : "#2e7d32";
	}
	if (t === "gtfsrt_rybnik") return "#880e4f";
	if (t === "gtfsrt_gzm") {
		let e = parseInt(r, 10);
		return !isNaN(e) && e <= 43 ? "#009b3a" : "#1565c0";
	}
	if (t === "gtfsrt_radom") return "#4a148c";
	if (t === "gtfsrt_suwalki") return "#283593";
	if (t === "gtfsrt_przemysl") return "#e65100";
	if (t === "gtfsrt_kutno") return "#006064";
	if (t === "gtfsrt_legnica") return "#b71c1c";
	if (t === "mpk_lodz") {
		let e = parseInt(r, 10);
		return !isNaN(e) && e <= 20 ? "#ad1457" : "#c62828";
	}
	return Ne[t] ? Ne[t] : "#005eb8";
}
function q(e) {
	return Array.isArray(e) ? e.map((e) => String(e).trim()).filter(Boolean) : e == null ? [] : String(e).split(",").map((e) => e.trim()).filter(Boolean);
}
function Ae(e) {
	if (typeof e == "string") return { entity: e };
	if (!e || typeof e != "object" || typeof e.entity != "string") return null;
	let t = { entity: e.entity };
	return "filter_routes" in e && (t.filter_routes = q(e.filter_routes)), "exclude_routes" in e && (t.exclude_routes = q(e.exclude_routes)), "max_departures" in e && (t.max_departures = Math.max(1, Math.min(100, parseInt(e.max_departures) || 0)) || null), "destination_filter" in e && (t.destination_filter = q(e.destination_filter)), "exclude_destinations" in e && (t.exclude_destinations = q(e.exclude_destinations)), "filter_vehicle_types" in e && (t.filter_vehicle_types = q(e.filter_vehicle_types).map((e) => e.toLowerCase())), "filter_providers" in e && (t.filter_providers = q(e.filter_providers)), "filter_platform" in e && (t.filter_platform = e.filter_platform == null ? "" : String(e.filter_platform)), "filter_track" in e && (t.filter_track = e.filter_track == null ? "" : String(e.filter_track)), "realtime_only" in e && (t.realtime_only = e.realtime_only === !0), "hide_terminus" in e && (t.hide_terminus = e.hide_terminus === !0), "hide_cancelled" in e && (t.hide_cancelled = e.hide_cancelled === !0), "highlight_mode" in e && (t.highlight_mode = e.highlight_mode === !0), t;
}
function J(e, t = "none") {
	if (!e || typeof e != "object") return { action: t };
	let n = { action: String(e.action || t).toLowerCase() };
	return e.navigation_path && (n.navigation_path = String(e.navigation_path)), e.url_path && (n.url_path = String(e.url_path)), e.perform_action && (n.perform_action = String(e.perform_action)), e.service && (n.service = String(e.service)), e.data && typeof e.data == "object" && (n.data = e.data), e.target && typeof e.target == "object" && (n.target = e.target), n;
}
function je(e, t, n = {}) {
	e.dispatchEvent(new CustomEvent(t, {
		detail: n,
		bubbles: !0,
		composed: !0
	}));
}
var Me = {
	kiedyprzyjedzie_pks_gdansk: "#475569",
	kiedyprzyjedzie_albatros: "#166534",
	kiedyprzyjedzie_gryf: "#2f2f2f",
	kiedyprzyjedzie_nord_express: "#9d174d",
	kiedyprzyjedzie_pks_gdynia: "#0f766e",
	kiedyprzyjedzie_mzk_malbork: "#14532d",
	kiedyprzyjedzie_pks_slupsk: "#0f172a",
	kiedyprzyjedzie_mzk_starogard: "#7f1d1d",
	kiedyprzyjedzie_pks_starogard: "#1e3a8a",
	kiedyprzyjedzie_bytow: "#155e75",
	kiedyprzyjedzie_czluchow: "#991b1b",
	time4bus_tczew: "#1d4ed8",
	gtfsrt_poznan: "#15803d",
	gtfsrt_lublin: "#0054a0",
	gtfsrt_kielce: "#006d3f",
	gtfsrt_radom: "#4a2080",
	gtfsrt_czestochowa: "#e30613",
	gtfsrt_elblag: "#003d7c",
	gtfsrt_gorzow: "#009640",
	gtfsrt_suwalki: "#2e5090",
	gtfsrt_przemysl: "#d4760a",
	gtfsrt_rybnik: "#8b1a2d",
	gtfsrt_kutno: "#0072bc",
	gtfsrt_legnica: "#d4213d",
	gtfsrt_gzm: "#009b3a",
	zbiorkom_krakow: "#e2001a",
	gtfsrt_szczecin: "#005ca9",
	gtfsrt_warszawa: "#c4161c",
	gtfsrt_elk: "#1a5276",
	gtfsrt_wkd: "#4a235a",
	gtfs_bialystok: "#1e40af",
	gtfs_olsztyn: "#065f46",
	gtfs_opole: "#7c2d12",
	gtfs_rzeszow: "#4338ca",
	gtfs_leszno: "#0f766e",
	mpk_lodz: "#e11d48"
}, Ne = {
	kiedyprzyjedzie_pks_gdansk: "#0f766e",
	kiedyprzyjedzie_albatros: "#22c55e",
	kiedyprzyjedzie_gryf: "#facc15",
	kiedyprzyjedzie_nord_express: "#ec4899",
	kiedyprzyjedzie_pks_gdynia: "#16a34a",
	kiedyprzyjedzie_mzk_malbork: "#d97706",
	kiedyprzyjedzie_pks_slupsk: "#2563eb",
	kiedyprzyjedzie_mzk_starogard: "#dc2626",
	kiedyprzyjedzie_pks_starogard: "#0ea5e9",
	kiedyprzyjedzie_bytow: "#14b8a6",
	kiedyprzyjedzie_czluchow: "#f97316",
	time4bus_tczew: "#dc2626",
	gtfsrt_poznan: "#22c55e",
	gtfsrt_lublin: "#3b82f6",
	gtfsrt_kielce: "#10b981",
	gtfsrt_radom: "#8b5cf6",
	gtfsrt_czestochowa: "#ef4444",
	gtfsrt_elblag: "#0ea5e9",
	gtfsrt_gorzow: "#34d399",
	gtfsrt_suwalki: "#6366f1",
	gtfsrt_przemysl: "#f59e0b",
	gtfsrt_rybnik: "#e11d48",
	gtfsrt_kutno: "#06b6d4",
	gtfsrt_legnica: "#f43f5e",
	gtfsrt_gzm: "#22c55e",
	zbiorkom_krakow: "#dc2626",
	gtfsrt_szczecin: "#2563eb",
	gtfsrt_warszawa: "#b91c1c",
	gtfsrt_elk: "#0369a1",
	gtfsrt_wkd: "#7c3aed",
	gtfs_bialystok: "#3b82f6",
	gtfs_olsztyn: "#10b981",
	gtfs_opole: "#f97316",
	gtfs_rzeszow: "#8b5cf6",
	gtfs_leszno: "#14b8a6",
	mpk_lodz: "#fb7185"
}, Y = (e) => ({ select: { options: e } }), Pe = [
	{
		name: "entities",
		selector: { entity: {
			multiple: !0,
			domain: "sensor"
		} }
	},
	{
		type: "grid",
		name: "",
		schema: [{
			name: "title",
			selector: { text: {} }
		}, {
			name: "icon",
			selector: { icon: {} }
		}]
	},
	{
		type: "grid",
		name: "",
		schema: [
			{
				name: "display_preset",
				selector: Y([
					{
						value: "standard",
						label: "Standard"
					},
					{
						value: "compact",
						label: "Compact"
					},
					{
						value: "minimal",
						label: "Minimal"
					},
					{
						value: "e_ink",
						label: "E-ink"
					}
				])
			},
			{
				name: "view_mode",
				selector: Y([{
					value: "mixed",
					label: "Mixed"
				}, {
					value: "tabs",
					label: "Tabs"
				}])
			},
			{
				name: "theme_mode",
				selector: Y([
					{
						value: "auto",
						label: "Auto (Home Assistant)"
					},
					{
						value: "light",
						label: "Light"
					},
					{
						value: "dark",
						label: "Dark"
					}
				])
			}
		]
	},
	{
		type: "grid",
		name: "",
		schema: [
			{
				name: "header_style",
				selector: Y([
					{
						value: "provider",
						label: "Provider color"
					},
					{
						value: "theme",
						label: "Home Assistant theme"
					},
					{
						value: "custom",
						label: "Custom color"
					}
				])
			},
			{
				name: "header_color",
				selector: { text: { type: "color" } }
			},
			{
				name: "show_header",
				selector: { boolean: {} }
			},
			{
				name: "show_clock",
				selector: { boolean: {} }
			}
		]
	},
	{
		type: "grid",
		name: "",
		schema: [
			{
				name: "max_departures",
				selector: { number: {
					min: 1,
					max: 100,
					mode: "box"
				} }
			},
			{
				name: "min_departures",
				selector: { number: {
					min: 0,
					max: 100,
					mode: "box"
				} }
			},
			{
				name: "refresh_interval",
				selector: { number: {
					min: 10,
					max: 600,
					mode: "box",
					unit_of_measurement: "s"
				} }
			},
			{
				name: "time_format",
				selector: Y([
					{
						value: "auto",
						label: "Auto (Home Assistant)"
					},
					{
						value: "24h",
						label: "24-hour"
					},
					{
						value: "12h",
						label: "12-hour"
					}
				])
			}
		]
	},
	{
		type: "expandable",
		title: "Rows",
		schema: [
			{
				name: "show_delays",
				selector: { boolean: {} }
			},
			{
				name: "show_countdown",
				selector: { boolean: {} }
			},
			{
				name: "show_vehicle",
				selector: { boolean: {} }
			},
			{
				name: "show_platform",
				selector: { boolean: {} }
			},
			{
				name: "show_accessibility",
				selector: { boolean: {} }
			},
			{
				name: "show_stop_name",
				selector: { boolean: {} }
			},
			{
				name: "show_footer",
				selector: { boolean: {} }
			},
			{
				name: "show_last_update",
				selector: { boolean: {} }
			},
			{
				name: "show_bike",
				selector: { boolean: {} }
			},
			{
				name: "show_wheelchair",
				selector: { boolean: {} }
			},
			{
				name: "show_ac",
				selector: { boolean: {} }
			},
			{
				name: "show_ticket_machine",
				selector: { boolean: {} }
			}
		]
	},
	{
		type: "expandable",
		title: "Filters",
		schema: [
			{
				name: "filter_routes",
				selector: { text: { multiple: !0 } }
			},
			{
				name: "exclude_routes",
				selector: { text: { multiple: !0 } }
			},
			{
				name: "destination_filter",
				selector: { text: { multiple: !0 } }
			},
			{
				name: "exclude_destinations",
				selector: { text: { multiple: !0 } }
			},
			{
				name: "filter_vehicle_types",
				selector: { text: { multiple: !0 } }
			},
			{
				name: "filter_providers",
				selector: { text: { multiple: !0 } }
			},
			{
				name: "filter_platform",
				selector: { text: {} }
			},
			{
				name: "filter_track",
				selector: { text: {} }
			},
			{
				name: "highlight_mode",
				selector: { boolean: {} }
			},
			{
				name: "hide_terminus",
				selector: { boolean: {} }
			},
			{
				name: "hide_cancelled",
				selector: { boolean: {} }
			},
			{
				name: "realtime_only",
				selector: { boolean: {} }
			}
		]
	}
], Fe = [{
	type: "grid",
	name: "",
	schema: [{
		name: "max_departures",
		selector: { number: {
			min: 1,
			max: 100,
			mode: "box"
		} }
	}]
}, {
	type: "expandable",
	title: "Filters",
	schema: [
		{
			name: "filter_routes",
			selector: { text: { multiple: !0 } }
		},
		{
			name: "exclude_routes",
			selector: { text: { multiple: !0 } }
		},
		{
			name: "destination_filter",
			selector: { text: { multiple: !0 } }
		},
		{
			name: "exclude_destinations",
			selector: { text: { multiple: !0 } }
		},
		{
			name: "filter_vehicle_types",
			selector: { text: { multiple: !0 } }
		},
		{
			name: "filter_providers",
			selector: { text: { multiple: !0 } }
		},
		{
			name: "filter_platform",
			selector: { text: {} }
		},
		{
			name: "filter_track",
			selector: { text: {} }
		},
		{
			name: "highlight_mode",
			selector: { boolean: {} }
		},
		{
			name: "hide_terminus",
			selector: { boolean: {} }
		},
		{
			name: "hide_cancelled",
			selector: { boolean: {} }
		},
		{
			name: "realtime_only",
			selector: { boolean: {} }
		}
	]
}], Ie = /* @__PURE__ */ new Set([
	"filter_routes",
	"exclude_routes",
	"destination_filter",
	"exclude_destinations",
	"filter_vehicle_types",
	"filter_providers"
]), Le = class extends B {
	static get properties() {
		return {
			hass: { type: Object },
			_config: { type: Object },
			_targetEntity: { state: !0 }
		};
	}
	static styles = o`
    :host { display: block; }
    .editor { display: flex; flex-direction: column; gap: 10px; }
    .override {
      border: 1px solid var(--divider-color, #e5e5e5);
      border-radius: 10px;
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      background: var(--secondary-background-color, rgba(0, 0, 0, 0.02));
    }
    .override-title { font-size: 13px; font-weight: 600; }
    .override-label { font-size: 12px; color: var(--secondary-text-color); }
    select {
      width: 100%;
      padding: 8px;
      border: 1px solid var(--divider-color, #ccc);
      border-radius: 6px;
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color, #111);
    }
  `;
	setConfig(e) {
		this._config = { ...e };
		let t = this._entries();
		(!this._targetEntity || !t.some((e) => e.entity === this._targetEntity)) && (this._targetEntity = t[0]?.entity || "");
	}
	_entries() {
		return (this._config?.entities || []).map((e) => typeof e == "string" ? { entity: e } : e).filter((e) => e && e.entity);
	}
	_formData() {
		return {
			...this._config,
			entities: this._entries().map((e) => e.entity)
		};
	}
	_selectedEntry() {
		return this._entries().find((e) => e.entity === this._targetEntity) || null;
	}
	_valueChanged(e) {
		if (!this._config || !this.hass) return;
		let t = { ...e.detail.value };
		Array.isArray(t.entities) && (t.entities = this._mergeEntitySelection(t.entities));
		for (let e of Ie) e in t && (t[e] = q(t[e]));
		this._config = {
			...this._config,
			...t
		}, this._dispatch();
	}
	_mergeEntitySelection(e) {
		let t = new Map(this._entries().map((e) => [e.entity, e]));
		return (Array.isArray(e) ? e : []).map((e) => {
			let n = typeof e == "string" ? e : e?.entity, r = t.get(n);
			return r && Object.keys(r).length > 1 ? r : n;
		}).filter(Boolean);
	}
	_targetChanged(e) {
		this._targetEntity = e.target.value;
	}
	_overrideChanged(e) {
		if (!this._config || !this._targetEntity) return;
		let t = { ...e.detail.value };
		for (let e of Ie) e in t && (t[e] = q(t[e]));
		let n = this._entries().map((e) => {
			if (e.entity !== this._targetEntity) return e;
			let n = {
				...e,
				...t,
				entity: e.entity
			};
			return Object.keys(n).length > 1 ? Ae(n) : e.entity;
		});
		this._config = {
			...this._config,
			entities: n
		}, this._dispatch();
	}
	_dispatch() {
		this.dispatchEvent(new CustomEvent("config-changed", {
			detail: { config: this._config },
			bubbles: !0,
			composed: !0
		}));
	}
	render() {
		if (!this.hass || !this._config) return N;
		let e = this._entries();
		return A`
      <div class="editor">
        <ha-form
          .hass=${this.hass}
          .data=${this._formData()}
          .schema=${Pe}
          .computeLabel=${(e) => this._computeLabel(e)}
          @value-changed=${this._valueChanged}
        ></ha-form>
        ${e.length ? A`
          <div class="override">
            <div class="override-title">${this._label("override_title")}</div>
            <div class="override-label">${this._label("override_hint")}</div>
            <select @change=${this._targetChanged} .value=${this._targetEntity}>
              ${e.map((e) => A`<option value=${e.entity} ?selected=${e.entity === this._targetEntity}>${e.entity.replace("sensor.", "")}</option>`)}
            </select>
            <ha-form
              .hass=${this.hass}
              .data=${this._selectedEntry() || {}}
              .schema=${Fe}
              .computeLabel=${(e) => this._computeLabel(e)}
              @value-changed=${this._overrideChanged}
            ></ha-form>
          </div>
        ` : N}
      </div>
    `;
	}
	_computeLabel(e) {
		return this._label(e.name);
	}
	_label(e) {
		return ((this.hass?.language || document.documentElement.lang || "en").slice(0, 2) === "pl" ? {
			entities: "Encje (sensory)",
			title: "Tytuł",
			icon: "Ikona",
			display_preset: "Motyw karty",
			view_mode: "Widok",
			theme_mode: "Motyw HA",
			header_style: "Styl nagłówka",
			header_color: "Kolor nagłówka",
			show_header: "Pokaż nagłówek",
			show_clock: "Pokaż zegar",
			max_departures: "Maks. odjazdów",
			min_departures: "Min. odjazdów (puste wiersze)",
			refresh_interval: "Odświeżanie",
			time_format: "Format czasu",
			show_delays: "Pokaż opóźnienia",
			show_countdown: "Pokaż odliczanie",
			show_vehicle: "Pokaż numer pojazdu",
			show_platform: "Pokaż peron / stanowisko",
			show_accessibility: "Pokaż ikony dostępności",
			show_stop_name: "Pokaż nazwę przystanku",
			show_footer: "Pokaż stopkę",
			show_last_update: "Pokaż czas aktualizacji",
			show_bike: "Rower",
			show_wheelchair: "Wózek",
			show_ac: "Klimatyzacja",
			show_ticket_machine: "Biletomat",
			filter_routes: "Linie — tylko",
			exclude_routes: "Linie — wyklucz",
			destination_filter: "Kierunki — tylko",
			exclude_destinations: "Kierunki — wyklucz",
			filter_vehicle_types: "Typ pojazdu (bus/tram/train)",
			filter_providers: "Providerzy",
			filter_platform: "Peron",
			filter_track: "Tor",
			highlight_mode: "Podświetlaj zamiast ukrywać",
			hide_terminus: "Ukryj kończące trasę",
			hide_cancelled: "Ukryj odwołane",
			realtime_only: "Tylko realtime",
			override_title: "Nadpisania per sensor",
			override_hint: "Puste pola dziedziczą ustawienia globalne."
		} : {
			entities: "Entities (sensors)",
			title: "Title",
			icon: "Icon",
			display_preset: "Card theme",
			view_mode: "View mode",
			theme_mode: "HA theme",
			header_style: "Header style",
			header_color: "Header color",
			show_header: "Show header",
			show_clock: "Show clock",
			max_departures: "Max departures",
			min_departures: "Min departures (padding)",
			refresh_interval: "Refresh interval",
			time_format: "Time format",
			show_delays: "Show delays",
			show_countdown: "Show countdown",
			show_vehicle: "Show vehicle number",
			show_platform: "Show platform / stand",
			show_accessibility: "Show accessibility icons",
			show_stop_name: "Show stop name",
			show_footer: "Show footer",
			show_last_update: "Show last update",
			show_bike: "Bike",
			show_wheelchair: "Wheelchair",
			show_ac: "A/C",
			show_ticket_machine: "Ticket machine",
			filter_routes: "Routes — include",
			exclude_routes: "Routes — exclude",
			destination_filter: "Destinations — include",
			exclude_destinations: "Destinations — exclude",
			filter_vehicle_types: "Vehicle type (bus/tram/train)",
			filter_providers: "Providers",
			filter_platform: "Platform",
			filter_track: "Track",
			highlight_mode: "Highlight instead of hiding",
			hide_terminus: "Hide terminus",
			hide_cancelled: "Hide cancelled",
			realtime_only: "Real-time only",
			override_title: "Per-sensor overrides",
			override_hint: "Empty fields inherit the global settings."
		})[e] || e;
	}
};
customElements.define("mzkzg-transport-card-editor", Le), customElements.define("polish-transport-card-editor", class extends Le {});
//#endregion
//#region node_modules/lit-html/directive.js
var Re = {
	ATTRIBUTE: 1,
	CHILD: 2,
	PROPERTY: 3,
	BOOLEAN_ATTRIBUTE: 4,
	EVENT: 5,
	ELEMENT: 6
}, ze = (e) => (...t) => ({
	_$litDirective$: e,
	values: t
}), Be = class {
	constructor(e) {}
	get _$AU() {
		return this._$AM._$AU;
	}
	_$AT(e, t, n) {
		this._$Ct = e, this._$AM = t, this._$Ci = n;
	}
	_$AS(e, t) {
		return this.update(e, t);
	}
	update(e, t) {
		return this.render(...t);
	}
}, X = class extends Be {
	constructor(e) {
		if (super(e), this.it = N, e.type !== Re.CHILD) throw Error(this.constructor.directiveName + "() can only be used in child bindings");
	}
	render(e) {
		if (e === N || e == null) return this._t = void 0, this.it = e;
		if (e === M) return e;
		if (typeof e != "string") throw Error(this.constructor.directiveName + "() called with a non-string value");
		if (e === this.it) return this._t;
		this.it = e;
		let t = [e];
		return t.raw = t, this._t = {
			_$litType$: this.constructor.resultType,
			strings: t,
			values: []
		};
	}
};
X.directiveName = "unsafeHTML", X.resultType = 1;
var Z = ze(X), Ve = o`
:host {
  display: block;
  --mzkzg-bg: var(--card-background-color, #fff);
  --mzkzg-text: var(--primary-text-color, #111);
  --mzkzg-muted: var(--secondary-text-color, #888);
  --mzkzg-divider: var(--divider-color, #e5e5e5);
  --mzkzg-focus: var(--primary-color, #3b82f6);
  --mzkzg-chip-bg: var(--chip-background, #e5e7eb);
  --mzkzg-chip-text: var(--chip-color, #374151);
  --mzkzg-header-text: #fff;
  --mzkzg-header-muted: rgba(255, 255, 255, 0.72);
  --mzkzg-live-dot: #10b981;
}
ha-card[data-theme="light"] {
  color-scheme: light;
  --mzkzg-bg: #fff;
  --mzkzg-text: #111827;
  --mzkzg-muted: #6b7280;
  --mzkzg-divider: #e5e7eb;
  --mzkzg-chip-bg: #eef1f5;
  --mzkzg-chip-text: #374151;
}
ha-card[data-theme="dark"] {
  color-scheme: dark;
  --mzkzg-bg: #1c1c1e;
  --mzkzg-text: #f2f2f7;
  --mzkzg-muted: #a1a1aa;
  --mzkzg-divider: #3a3a3c;
  --mzkzg-chip-bg: #2c2c2e;
  --mzkzg-chip-text: #f2f2f7;
  --mzkzg-header-text: #fff;
  --mzkzg-header-muted: rgba(255, 255, 255, 0.72);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
ha-card {
  display: block;
  overflow: hidden;
  font-family: var(--ha-card-header-font-family, inherit);
  background: var(--mzkzg-bg);
  color: var(--mzkzg-text);
  border-radius: var(--ha-card-border-radius, 12px);
  box-shadow: var(--ha-card-box-shadow, none);
}
.header {
  padding: 8px 12px; display: flex; align-items: center; gap: 8px; user-select: none;
}
.header-icon { display: flex; align-items: center; justify-content: center; flex-shrink: 0; width: 24px; height: 24px; color: var(--mzkzg-header-text); }
.header-icon svg { width: 18px; height: 18px; }
.header-body { flex: 1; min-width: 0; }
.header-title { color: var(--mzkzg-header-text); font-size: 14px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.header-sub { color: var(--mzkzg-header-muted); font-size: 10px; margin-top: 1px; }
.header-clock { color: var(--mzkzg-header-text); font-size: 13px; font-weight: 600; font-variant-numeric: tabular-nums; opacity: 0.9; white-space: nowrap; }
.dep-list { list-style: none; }
.dep-row { transition: opacity 0.4s, max-height 0.4s, padding 0.4s; max-height: 80px; overflow: hidden; }
.dep-row.departing { opacity: 0; max-height: 0; padding-top: 0; padding-bottom: 0; }
ha-card.e-ink .dep-row { transition: none; }
.tabs { display: flex; overflow-x: auto; scrollbar-width: none; border-bottom: 1px solid var(--divider-color, #e5e5e5); }
.tabs::-webkit-scrollbar { display: none; }
.tab { flex: 1 0 auto; min-width: max-content; padding: 8px 14px; font-size: 12px; font-weight: 600; color: var(--mzkzg-muted); cursor: pointer; white-space: nowrap; border-bottom: 2px solid transparent; text-align: center; }
.tab.active { color: var(--mzkzg-text); border-bottom-color: var(--primary-color, #005eb8); }
.tab:hover { color: var(--mzkzg-text); }
.tab:focus-visible { outline: 2px solid var(--mzkzg-focus); outline-offset: -2px; }
.provider-header { padding: 4px 14px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; background: var(--secondary-background-color, rgba(0, 0, 0, 0.04)); color: var(--mzkzg-muted); border-bottom: 1px solid var(--mzkzg-divider); border-top: 1px solid var(--mzkzg-divider); margin-top: -1px; }
.dep-row {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; border-bottom: 1px solid var(--mzkzg-divider); min-height: 52px;
}
.dep-row.interactive { cursor: pointer; }
.dep-row:focus-visible { outline: 2px solid var(--mzkzg-focus); outline-offset: -2px; }
.dep-row:last-child { border-bottom: none; }
.dep-row.imminent { }
.dep-row.dimmed { opacity: 0.35; }
.badge {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 3px 7px; border-radius: 6px; font-size: 13px; font-weight: 700;
  color: #fff; min-width: 40px; flex-shrink: 0;
}
.headsign {
  font-size: 13px; font-weight: 500; color: var(--mzkzg-text);
  flex: 1; min-width: 0; display: flex; flex-wrap: wrap; align-items: center; gap: 2px 6px;
}
.head-main { display: inline-flex; align-items: center; gap: 6px; width: 100%; min-width: 0; }
.headsign-text { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 0 1 auto; min-width: 0; max-width: 100%; }
.icons { display: inline-flex; gap: 3px; align-items: center; flex-shrink: 0; white-space: nowrap; flex-basis: 100%; width: 100%; margin-top: 1px; }
.icons svg { color: var(--mzkzg-muted); opacity: 0.8; }
.map-pin { display: inline-flex; align-items: center; color: var(--mzkzg-focus); opacity: 0.85; }
.platform { display: inline-flex; align-items: center; justify-content: center; background: var(--mzkzg-chip-bg); color: var(--mzkzg-chip-text); border-radius: 6px; padding: 1px 6px; font-size: 10px; font-weight: 600; letter-spacing: 0.02em; white-space: nowrap; flex-shrink: 0; }
.meta-row { display: inline-flex; align-items: center; gap: 6px; flex-wrap: wrap; width: 100%; margin-top: 1px; }
.stop-name { display: block; font-size: 10px; color: var(--mzkzg-muted); font-weight: 400; margin-top: 1px; width: 100%; }
ha-card.minimal .header,
ha-card.minimal .footer,
ha-card.minimal .stop-name,
ha-card.minimal .icons,
ha-card.minimal .map-pin,
ha-card.minimal .platform { display: none; }
ha-card.minimal .dep-row { min-height: 34px; padding: 5px 10px; gap: 8px; }
ha-card.minimal .badge { min-width: 32px; padding: 2px 5px; font-size: 11px; }
ha-card.minimal .headsign { font-size: 12px; }
ha-card.minimal .time-main { font-size: 13px; }
ha-card.minimal .time-sub { font-size: 10px; }
ha-card.compact .stop-name { display: none; }
ha-card.compact .icons { display: none; }
ha-card.compact .meta-row { display: none; }
ha-card.compact .platform { display: none; }
ha-card.compact .footer { display: none; }
.dep-row.cancelled .headsign { text-decoration: line-through; opacity: 0.6; }
.dep-row.cancelled .badge { opacity: 0.5; }
.time-main.cancelled { font-size: 12px; color: #dc2626; font-weight: 600; }
.provider-header { color: var(--mzkzg-muted); }

.time-col { text-align: right; flex-shrink: 0; display: flex; flex-direction: column; align-items: flex-end; gap: 1px; }
.time-main { font-size: 15px; font-weight: 600; color: var(--mzkzg-text); white-space: nowrap; }
.time-struck { text-decoration: line-through; opacity: 0.5; font-size: 13px; font-weight: 400; }
.time-sub { font-size: 11px; color: var(--mzkzg-muted); white-space: nowrap; display: flex; align-items: center; gap: 4px; }
.time-sub .dot { color: var(--mzkzg-live-dot); font-weight: 700; display: inline-block; animation: live-dot-pulse 2s ease-in-out infinite; transform-origin: center; }
@keyframes live-dot-pulse { 0%,100% { opacity: 1; transform: scale(1); } 50% { opacity: .35; transform: scale(.72); } }
@media (prefers-reduced-motion: reduce) { .time-sub .dot { animation: none; } }
.delay-badge { font-size: 11px; font-weight: 600; }
.delay-badge.late { color: #dc2626; }
.delay-badge.early { color: #0369a1; }
.state-msg { padding: 24px 16px; text-align: center; color: var(--mzkzg-muted); font-size: 13px; }
.state-msg .icon { font-size: 28px; display: block; margin-bottom: 8px; }
.footer { padding: 5px 14px; font-size: 10px; color: var(--mzkzg-muted); text-align: right; border-top: 1px solid var(--mzkzg-divider); }
.skel { background: var(--divider-color, #e5e5e5); border-radius: 4px; }
@keyframes shimmer { 0%,100%{opacity:.5} 50%{opacity:1} }
.skel { animation: shimmer 1.4s ease-in-out infinite; }

/* Vehicle map modal */
.map-overlay {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0,0,0,0.5); z-index: 1000;
  display: flex; align-items: center; justify-content: center;
}
.map-wrap {
  position: relative; width: 90%; max-width: 500px; height: 60vh; max-height: 400px;
  background: #fff; border-radius: 12px; overflow: hidden;
  box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
.map-wrap .leaflet-container { border-radius: 12px; }
.map-close {
  position: absolute; top: 8px; right: 8px; z-index: 1001;
  background: rgba(255,255,255,0.9); border: none; border-radius: 50%;
  width: 32px; height: 32px; cursor: pointer; font-size: 18px;
  display: flex; align-items: center; justify-content: center;
  color: #333; box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}
.map-close:hover { background: #fff; }

/* e-ink */
ha-card.e-ink { background: #fff; color: #000; border: 0; border-radius: 0; box-shadow: none; }
ha-card.e-ink .header { background: #fff !important; border-bottom: 2px solid #000; }
ha-card.e-ink .header-title, ha-card.e-ink .header-sub, ha-card.e-ink .header-icon { color: #000; }
ha-card.e-ink .header-icon ha-icon { color: #000 !important; --mdc-icon-size: 20px; }
ha-card.e-ink .stop-name, ha-card.e-ink .platform, ha-card.e-ink .icons, ha-card.e-ink .time-sub, ha-card.e-ink .footer { display: none; }
ha-card.e-ink .dep-row { border-bottom-color: #000; }
ha-card.e-ink .badge { background: #fff !important; border: 2px solid #000; color: #000; }
ha-card.e-ink .dep-row.imminent { background: #fff; }
ha-card.e-ink .headsign, ha-card.e-ink .time-main, ha-card.e-ink .state-msg { color: #000; }
ha-card.e-ink .time-sub .dot, ha-card.e-ink .delay-badge, ha-card.e-ink .delay-badge.late, ha-card.e-ink .delay-badge.early { color: #000; }
ha-card.e-ink .skel { animation: none; }

/* compact */
ha-card.compact .header { padding: 9px 12px; gap: 8px; }
ha-card.compact .header-icon { width: 24px; height: 24px; }
ha-card.compact .header-icon svg { width: 19px; height: 19px; }
ha-card.compact .header-title { font-size: 14px; }
ha-card.compact .header-sub { font-size: 10px; }
ha-card.compact .dep-list { padding-top: 4px; }
ha-card.compact .dep-row { min-height: 40px; padding: 6px 12px; gap: 8px; }
ha-card.compact .badge { min-width: 34px; padding: 2px 6px; font-size: 12px; }
ha-card.compact .headsign { font-size: 12px; }
ha-card.compact .time-main { font-size: 13px; }
ha-card.compact .time-sub { font-size: 10px; }
ha-card.compact .footer { padding: 5px 12px; }

/* Responsive — small cards (< 300px width) */
@container (max-width: 300px) {
  .header { padding: 10px 10px; gap: 8px; }
  .header-icon { width: 22px; height: 22px; }
  .header-icon svg { width: 17px; height: 17px; }
  .header-title { font-size: 13px; }
  .header-sub { font-size: 9px; }
  .dep-row { padding: 8px 10px; gap: 8px; min-height: 40px; }
  .badge { min-width: 34px; padding: 2px 5px; font-size: 11px; }
  .headsign { font-size: 12px; }
  .time-main { font-size: 13px; }
  .time-sub { font-size: 10px; }
  .icons { gap: 2px; }
  .platform { font-size: 9px; padding: 1px 3px; }
  .tab { padding: 6px 8px; font-size: 11px; }
  .footer { font-size: 9px; padding: 4px 10px; }
}

/* Responsive — large cards (> 500px width, e.g. tablet panels) */
@container (min-width: 500px) {
  .header { padding: 16px 18px; }
  .header-title { font-size: 17px; }
  .header-sub { font-size: 12px; }
  .dep-row { padding: 12px 18px; gap: 12px; }
  .badge { min-width: 46px; padding: 4px 9px; font-size: 14px; }
  .headsign { font-size: 14px; }
  .time-main { font-size: 16px; }
  .time-sub { font-size: 12px; }
  .footer { padding: 6px 18px; font-size: 11px; }
}

/* Container query setup */
:host { container-type: inline-size; }
ha-card { container-type: inline-size; }
`, Q = null, $ = null, He = class {
	constructor(e) {
		this.card = e;
	}
	destroy() {
		this.mapCtx && this.mapCtx.destroy();
	}
	ensureLeafletCss() {
		return $ || ($ = new Promise((e) => {
			let t = document.getElementById("polish-transport-leaflet-css");
			if (t) {
				if (t.sheet) {
					e();
					return;
				}
				t.addEventListener("load", () => e(), { once: !0 }), t.addEventListener("error", () => e(), { once: !0 });
				return;
			}
			let n = document.createElement("link");
			n.id = "polish-transport-leaflet-css", n.rel = "stylesheet", n.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css", n.addEventListener("load", () => e(), { once: !0 }), n.addEventListener("error", () => e(), { once: !0 }), document.head.appendChild(n);
		}), $);
	}
	preloadLeaflet() {
		return Q || (Q = this.ensureLeafletCss().then(() => window.L ? window.L : new Promise((e, t) => {
			let n = document.getElementById("polish-transport-leaflet-js");
			n || (n = document.createElement("script"), n.id = "polish-transport-leaflet-js", n.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js", document.head.appendChild(n));
			let r = () => {
				n.removeEventListener("error", i), e(window.L);
			}, i = () => {
				n.removeEventListener("load", r), n.remove(), Q = null, t(/* @__PURE__ */ Error("Failed to load Leaflet"));
			};
			n.addEventListener("load", r, { once: !0 }), n.addEventListener("error", i, { once: !0 });
		})), Q);
	}
	buildVehicleMarker(e, t, n, r, i, a) {
		let o = a ? 32 : 40, s = a ? 11 : 13, c = o / 2, l = e + 180;
		return {
			svg: `<svg xmlns="http://www.w3.org/2000/svg" width="${o}" height="${o + 6}" viewBox="0 0 ${o} ${o + 6}">
      <circle cx="${c}" cy="${c}" r="${c - 3}" fill="${t}" stroke="#fff" stroke-width="1.5"/>
      <path d="M${c},${o - 3} Q${c - 14},${o + 1} ${c - 7},${o - 1} L${c},${o + 6} L${c + 7},${o - 1} Q${c + 14},${o + 1} ${c},${o - 3} Z" fill="${t}" stroke="#fff" stroke-width="1.5" stroke-linejoin="round" transform="rotate(${l}, ${c}, ${c})"/>
      <text x="${c}" y="${c}" text-anchor="middle" dominant-baseline="central" font-weight="700" font-size="${s}" fill="#fff" font-family="system-ui,sans-serif">${U(n)}</text>
    </svg>`,
			size: o,
			arrowH: o + 6
		};
	}
	buildPopupContent(e) {
		let t = Math.round((e.delay_seconds || 0) / 60), n = t > 0 ? `+${t} min` : t < 0 ? `${t} min` : "o czasie", r = t > 0 ? "zm-popup-delay" : t < 0 ? "zm-popup-delay early" : "zm-popup-delay ontime";
		return `<div class="zm-popup"><div class="zm-popup-route">${U(e.route)}</div>${e.headsign ? `<div class="zm-popup-headsign">→ ${U(e.headsign)}</div>` : ""}${e.vehicle_code ? `<div class="zm-popup-meta">🚍 ${U(e.vehicle_code)}</div>` : ""}<div class="zm-popup-delay-row"><span class="${r}">${U(n)}</span></div></div>`;
	}
	showVehicleMap(e, t, n) {
		this.mapCtx && this.mapCtx.destroy();
		let r = window.innerWidth < 480, i = Math.min(window.innerWidth * .92, 520), a = Math.min(window.innerHeight * .65, 420), o = document.createElement("div");
		o.style.cssText = "position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:100000;display:flex;align-items:center;justify-content:center;", o.innerHTML = `<div style="position:relative;width:${i}px;height:${a}px;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,0.3);"><button style="position:absolute;top:8px;right:8px;z-index:1001;background:rgba(0,0,0,0.6);border:none;border-radius:50%;width:32px;height:32px;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;color:#fff;">✕</button><div id="vmap" style="width:${i}px;height:${a}px;"></div><div id="vmap-status" style="position:absolute;bottom:6px;left:10px;z-index:1001;font-size:10px;color:#999;background:rgba(255,255,255,0.8);padding:2px 6px;border-radius:4px">🔄 odświeżanie co 30s</div></div>`, document.body.appendChild(o);
		let s = () => {
			this.mapCtx && this.mapCtx.destroy();
		};
		o.querySelector("button").onclick = s, o.onclick = (e) => {
			e.target === o && s();
		};
		let c = o.querySelector("#vmap");
		if (!document.getElementById("ztm-map-style")) {
			let e = document.createElement("style");
			e.id = "ztm-map-style", e.textContent = ".zm-arrow{position:relative;display:inline-block;transition:transform 0.8s ease}.zm-arrow svg{display:block}.zm-popup{font-family:system-ui,sans-serif;font-size:12px;line-height:1.3;min-width:120px}.zm-popup-route{font-size:22px;font-weight:800;line-height:1}.zm-popup-headsign{font-size:13px;color:#555}.zm-popup-meta{font-size:10px;color:#999;margin-top:2px}.zm-popup-delay-row{margin-top:4px;font-size:13px;font-weight:600}.zm-popup-delay{color:#e53935}.zm-popup-delay.ontime{color:#43a047}.zm-popup-delay.early{color:#1e88e5}}", document.head.appendChild(e);
		}
		let l = {
			destroyed: !1,
			map: null,
			interval: null,
			ro: null,
			markers: [],
			overlay: o,
			onKeyDown: null,
			destroy: () => {
				l.destroyed = !0, l.interval && clearInterval(l.interval), l.ro && l.ro.disconnect(), l.map &&= (l.map.remove(), null), l.onKeyDown &&= (document.removeEventListener("keydown", l.onKeyDown), null), l.overlay && l.overlay.parentNode && l.overlay.parentNode.removeChild(l.overlay), this.mapCtx === l && (this.mapCtx = null);
			},
			entityId: n.entityId,
			vehicleCode: n.code
		};
		this.mapCtx = l, l.onKeyDown = (e) => {
			e.key === "Escape" && s();
		}, document.addEventListener("keydown", l.onKeyDown);
		let u = K(n.route, n.provider || "", n.route_color);
		this.preloadLeaflet().then(() => {
			requestAnimationFrame(() => {
				if (l.destroyed) return;
				let i = window.L.map(c, { zoomControl: !0 }).setView([e, t], 16);
				this.addTileLayer(i, l);
				let a = i.attributionControl.options.prefix;
				if (a && i.attributionControl.setPrefix(a.replace(/<a /g, "<a target=\"_blank\" rel=\"noopener\" ")), l.map = i, window.L.circleMarker([e, t], {
					radius: 5,
					fillColor: u,
					fillOpacity: .5,
					color: "#fff",
					weight: 2
				}).addTo(i), this.renderAllVehicleMarkers(l, n, r), n.provider === "ztm_gdansk" && n.route_id_int && n.trip_id) {
					let e = `https://ckan2.multimediagdansk.pl/shapes?date=${(/* @__PURE__ */ new Date()).toISOString().split("T")[0]}&routeId=${n.route_id_int}&tripId=${n.trip_id}`;
					fetch(e).then((e) => e.json()).then((e) => {
						if (!(l.destroyed || !l.map) && e && e.coordinates && Array.isArray(e.coordinates)) {
							let t = e.coordinates.map((e) => [e[1], e[0]]), r = K(n.route, n.provider) || "#e53935";
							window.L.polyline(t, {
								color: r,
								weight: 4,
								opacity: .8
							}).addTo(l.map);
						}
					}).catch((e) => console.warn("Failed to load shape for Gdańsk:", e));
				}
				l.ro = new window.ResizeObserver(() => {
					l.map && l.map.invalidateSize();
				}), l.ro.observe(c), l.interval = setInterval(() => this.updateAllVehiclePositions(l), 3e4);
			});
		}).catch(() => l.destroy());
	}
	async addTileLayer(e, t) {
		let n = () => this.card.hass.callWS({ type: "map_tiles/access_token" }).then((e) => e?.token || null, () => null), r;
		try {
			r = await n();
		} catch {
			r = null;
		}
		if (t.destroyed) return;
		let i = (this.card.hass.auth?.data?.hassUrl || location.origin).replace(/\/+$/, ""), a = (e) => `${i}/api/map_tiles/raster/{z}/{x}/{y}.png?token=${encodeURIComponent(e)}`, o = window.L.tileLayer(r ? a(r) : "https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
			maxZoom: 19,
			attribution: "&copy; <a href=\"https://www.openstreetmap.org/copyright\" target=\"_blank\" rel=\"noopener\">OpenStreetMap</a> contributors",
			referrerPolicy: r ? void 0 : "strict-origin-when-cross-origin"
		}).addTo(e);
		if (!r) return;
		let s = 0;
		o.on("tileerror", async () => {
			if (Date.now() - s < 3e4) return;
			s = Date.now();
			let e = await n();
			e && !t.destroyed && o.setUrl(a(e));
		});
	}
	renderAllVehicleMarkers(e, t, n) {
		if (!this.card.hass) return;
		let r = this.card.hass.states[e.entityId];
		if (!r?.attributes?.departures) return;
		e.markers.forEach((t) => e.map.removeLayer(t)), e.markers = [];
		let i = !1, a = r.attributes.departures || [];
		for (let t of a) {
			let r = W(t.vehicle_lat, t.vehicle_lng);
			if (!r) continue;
			let a = t.vehicle_code && t.vehicle_code === e.vehicleCode, o = K(t.route, t._provider || t.provider || "", t.route_color), s = t.vehicle_direction || t.direction || 0;
			a && (i = !0);
			let c = t.route || "?", l = s, u = this.buildVehicleMarker(l, o, c, t.vehicle_type || "bus", t, n), d = `<div class="zm-arrow" style="opacity:${a ? 1 : .7}">${u.svg}</div>`, f = window.L.divIcon({
				className: "",
				html: d,
				iconSize: [u.size, u.arrowH],
				iconAnchor: [u.size / 2, u.arrowH]
			}), p = window.L.marker([r[0], r[1]], { icon: f }).addTo(e.map);
			e.markers.push(p);
		}
		!i && e.markers.length;
	}
	updateAllVehiclePositions(e) {
		if (e.destroyed || !e.entityId || !e.map || !this.card.hass) return;
		let t = this.card.hass.states[e.entityId];
		if (!t?.attributes?.departures) return;
		let n = t.attributes.departures || [];
		e.markers.forEach((t) => e.map.removeLayer(t)), e.markers = [];
		let r = window.innerWidth < 480;
		for (let t of n) {
			let n = W(t.vehicle_lat, t.vehicle_lng);
			if (!n) continue;
			let i = t.vehicle_code && t.vehicle_code === e.vehicleCode, a = K(t.route, t._provider || t.provider || "", t.route_color), o = t.vehicle_direction || t.direction || 0, s = t.route || "?", c = this.buildVehicleMarker(o, a, s, t.vehicle_type || "bus", t, r), l = `<div class="zm-arrow" style="opacity:${i ? 1 : .7}">${c.svg}</div>`, u = window.L.divIcon({
				className: "",
				html: l,
				iconSize: [c.size, c.arrowH],
				iconAnchor: [c.size / 2, c.arrowH]
			});
			e.markers.push(window.L.marker([n[0], n[1]], { icon: u }).addTo(e.map));
		}
	}
	updateVehiclePosition(e) {
		if (e.destroyed || !e.entityId || !e.marker || !this.card.hass) return;
		let t = this.card.hass.states[e.entityId];
		if (t?.attributes?.departures) {
			for (let n of t.attributes.departures) if (n.vehicle_code && n.vehicle_code === e.vehicleCode) {
				let t = W(n.vehicle_lat, n.vehicle_lng);
				if (!t) continue;
				let [r, i] = t, a = e.marker.getLatLng();
				if (Math.abs(a.lat - r) < 1e-5 && Math.abs(a.lng - i) < 1e-5) return;
				e.marker.setLatLng([r, i]);
				let o = n.vehicle_direction || n.direction || 0, s = K(n.route, n._provider || n.provider || "", n.route_color), c = n.vehicle_type || "bus", l = window.innerWidth < 480, u = this.buildVehicleMarker(o, s, n.route, c, n, l), d = `<div class="zm-arrow">${u.svg}</div>`;
				e.marker.setIcon(window.L.divIcon({
					className: "",
					html: d,
					iconSize: [u.size, u.arrowH],
					iconAnchor: [u.size / 2, u.arrowH]
				})), e.map.setView([r, i], e.map.getZoom(), { animate: !0 });
				break;
			}
		}
	}
}, Ue = j`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M16 16.01L16.01 15.99"/><path d="M6 16.01L6.01 15.99"/><path d="M20 22V15V8M20 8H18V2H22V8H20Z"/><path d="M4 20V22H6V20H4Z" fill="currentColor"/><path d="M14 20V22H16V20H14Z" fill="currentColor"/><path d="M16 20H2.6A.6.6 0 012 19.4V12.6c0-.33.27-.6.6-.6H16"/><path d="M14 8H6M14 2H6C3.79 2 2 3.79 2 6V8"/></svg>`, We = j`<svg viewBox="0 0 24 24" width="20" height="20" style="color:#fff"><path fill="currentColor" d="M12,2C8,2 4,2.5 4,6V15.5A3.5,3.5 0 0,0 7.5,19L6,20.5V21H18V20.5L16.5,19A3.5,3.5 0 0,0 20,15.5V6C20,2.5 16,2 12,2M7.5,17A1.5,1.5 0 0,1 6,15.5A1.5,1.5 0 0,1 7.5,14A1.5,1.5 0 0,1 9,15.5A1.5,1.5 0 0,1 7.5,17M11,10H6V7H11V10M13,10V7H18V10H13M16.5,17A1.5,1.5 0 0,1 15,15.5A1.5,1.5 0 0,1 16.5,14A1.5,1.5 0 0,1 18,15.5A1.5,1.5 0 0,1 16.5,17Z"/></svg>`, Ge = j`<svg viewBox="0 0 24 24" width="20" height="20" style="color:#fff"><path fill="currentColor" d="M14,14A2,2 0 0,1 12,16A2,2 0 0,1 10,14A2,2 0 0,1 12,12A2,2 0 0,1 14,14M12,19C10.74,19 9.38,18.42 8.44,17.44L10,15.93C10.55,16.29 11.23,16.5 12,16.5C12.77,16.5 13.45,16.29 14,15.93L15.56,17.44C14.62,18.42 13.26,19 12,19M20,6C20,4.89 19.11,4 18,4H6C4.89,4 4,4.89 4,6V18C4,19.11 4.89,20 6,20H18C19.11,20 20,19.11 20,18V6M12,10A4,4 0 0,0 8,14A4,4 0 0,0 12,18A4,4 0 0,0 16,14A4,4 0 0,0 12,10M17.5,7C17.22,7 17,6.78 17,6.5C17,6.22 17.22,6 17.5,6C17.78,6 18,6.22 18,6.5C18,6.78 17.78,7 17.5,7M15,7C14.72,7 14.5,6.78 14.5,6.5C14.5,6.22 14.72,6 15,6C15.28,6 15.5,6.22 15.5,6.5C15.5,6.78 15.28,7 15,7Z"/></svg>`, Ke = "<svg viewBox=\"0 0 24 24\" width=\"14\" height=\"14\"><path fill=\"currentColor\" d=\"M5,20.5A3.5,3.5 0 0,1 1.5,17A3.5,3.5 0 0,1 5,13.5A3.5,3.5 0 0,1 8.5,17A3.5,3.5 0 0,1 5,20.5M5,12A5,5 0 0,0 0,17A5,5 0 0,0 5,22A5,5 0 0,0 10,17A5,5 0 0,0 5,12M14.8,10H19V8.2H15.8L13.86,4.93C13.57,4.43 13,4.1 12.4,4.1C11.93,4.1 11.5,4.29 11.2,4.6L7.5,8.29C7.19,8.6 7,9 7,9.5C7,10.13 7.33,10.66 7.85,10.97L11.2,13V18H13V11.5L10.75,9.85L13.07,7.5M19,20.5A3.5,3.5 0 0,1 15.5,17A3.5,3.5 0 0,1 19,13.5A3.5,3.5 0 0,1 22.5,17A3.5,3.5 0 0,1 19,20.5M19,12A5,5 0 0,0 14,17A5,5 0 0,0 19,22A5,5 0 0,0 24,17A5,5 0 0,0 19,12M16,4.8C17,4.8 17.8,4 17.8,3C17.8,2 17,1.2 16,1.2C15,1.2 14.2,2 14.2,3C14.2,4 15,4.8 16,4.8Z\"/></svg>", qe = "<svg viewBox=\"0 0 24 24\" width=\"14\" height=\"14\"><path fill=\"currentColor\" d=\"M18.4,11.2L14.3,11.4L16.6,8.8C16.8,8.5 16.9,8 16.8,7.5C16.7,7.2 16.6,6.9 16.3,6.7L10.9,3.5C10.5,3.2 9.9,3.3 9.5,3.6L6.8,6.1C6.3,6.6 6.2,7.3 6.7,7.8C7.1,8.3 7.9,8.3 8.4,7.9L10.4,6.1L12.3,7.2L8.1,11.5C8,11.6 8,11.7 7.9,11.7C7.4,11.9 6.9,12.1 6.5,12.4L8,13.9C8.5,13.7 9,13.5 9.5,13.5C11.4,13.5 13,15.1 13,17C13,17.6 12.9,18.1 12.6,18.5L14.1,20C14.7,19.1 15,18.1 15,17C15,15.8 14.6,14.6 13.9,13.7L17.2,13.4L17,18.2C16.9,18.9 17.4,19.4 18.1,19.5H18.2C18.8,19.5 19.3,19 19.4,18.4L19.6,12.5C19.6,12.2 19.5,11.8 19.3,11.6C19,11.3 18.7,11.2 18.4,11.2M18,5.5A2,2 0 0,0 20,3.5A2,2 0 0,0 18,1.5A2,2 0 0,0 16,3.5A2,2 0 0,0 18,5.5M12.5,21.6C11.6,22.2 10.6,22.5 9.5,22.5C6.5,22.5 4,20 4,17C4,15.9 4.3,14.9 4.9,14L6.4,15.5C6.2,16 6,16.5 6,17C6,18.9 7.6,20.5 9.5,20.5C10.1,20.5 10.6,20.4 11,20.1L12.5,21.6Z\"/></svg>", Je = "<svg viewBox=\"0 0 24 24\" width=\"14\" height=\"14\"><path fill=\"currentColor\" d=\"M20.79,13.95L18.46,14.57L16.46,13.44V10.56L18.46,9.43L20.79,10.05L21.31,8.12L19.54,7.65L20,5.88L18.07,5.36L17.45,7.69L15.45,8.82L13,7.38V5.12L14.71,3.41L13.29,2L12,3.29L10.71,2L9.29,3.41L11,5.12V7.38L8.5,8.82L6.5,7.69L5.92,5.36L4,5.88L4.47,7.65L2.7,8.12L3.22,10.05L5.55,9.43L7.55,10.56V13.45L5.55,14.58L3.22,13.96L2.7,15.89L4.47,16.36L4,18.12L5.93,18.64L6.55,16.31L8.55,15.18L11,16.62V18.88L9.29,20.59L10.71,22L12,20.71L13.29,22L14.7,20.59L13,18.88V16.62L15.5,15.17L17.5,16.3L18.12,18.63L20,18.12L19.53,16.35L21.3,15.88L20.79,13.95M9.5,10.56L12,9.11L14.5,10.56V13.44L12,14.89L9.5,13.44V10.56Z\"/></svg>", Ye = "<svg viewBox=\"0 0 24 24\" width=\"14\" height=\"14\"><path fill=\"currentColor\" d=\"M12,2C8.13,2 5,5.13 5,9C5,14.25 12,22 12,22C12,22 19,14.25 19,9C19,5.13 15.87,2 12,2M12,11.5A2.5,2.5 0 0,1 9.5,9A2.5,2.5 0 0,1 12,6.5A2.5,2.5 0 0,1 14.5,9A2.5,2.5 0 0,1 12,11.5Z\"/></svg>", Xe = class extends B {
	static get properties() {
		return {
			hass: { type: Object },
			_config: { state: !0 },
			_activeTab: { state: !0 }
		};
	}
	static styles = Ve;
	constructor() {
		super(), this.vehicleMap = new He(this), this._config = {}, this._activeTab = 0, this._tickTimer = null;
	}
	static getStubConfig() {
		return {
			type: "custom:polish-transport-card",
			entities: [],
			max_departures: 10,
			min_departures: 5,
			show_delays: !0,
			hide_terminus: !0,
			show_bike: !0,
			show_wheelchair: !0,
			show_footer: !0
		};
	}
	static getConfigElement() {
		return document.createElement("mzkzg-transport-card-editor");
	}
	setConfig(e) {
		if (!e) throw Error("No configuration provided");
		if (e.entities && !Array.isArray(e.entities)) throw Error("entities must be an array");
		let t = [
			"standard",
			"compact",
			"e_ink",
			"minimal"
		].includes(e.display_preset) ? e.display_preset : "standard", n = [
			"auto",
			"light",
			"dark"
		].includes(e.theme_mode) ? e.theme_mode : "auto", r = [
			"provider",
			"theme",
			"custom"
		].includes(e.header_style) ? e.header_style : e.header_color ? "custom" : "provider";
		this._config = {
			...e,
			entities: (Array.isArray(e.entities) ? e.entities : []).map(Ae).filter(Boolean),
			max_departures: Math.max(1, Math.min(100, parseInt(e.max_departures) || 10)),
			min_departures: Math.max(0, Math.min(100, parseInt(e.min_departures) || 0)),
			refresh_interval: Math.max(5, Math.min(600, parseInt(e.refresh_interval) || 60)),
			display_preset: t,
			view_mode: e.view_mode === "tabs" ? "tabs" : "mixed",
			theme_mode: n,
			header_style: r,
			show_header: e.show_header !== !1,
			show_clock: e.show_clock === !0,
			show_delays: e.show_delays !== !1,
			hide_terminus: e.hide_terminus !== !1,
			hide_cancelled: e.hide_cancelled === !0,
			realtime_only: e.realtime_only === !0,
			highlight_mode: e.highlight_mode === !0,
			show_countdown: e.show_countdown !== !1,
			show_vehicle: e.show_vehicle !== !1,
			show_platform: e.show_platform !== !1,
			show_accessibility: e.show_accessibility !== !1,
			show_bike: e.show_bike !== !1,
			show_wheelchair: e.show_wheelchair !== !1,
			show_ac: e.show_ac !== !1,
			show_ticket_machine: e.show_ticket_machine !== !1,
			show_stop_name: e.show_stop_name === !0,
			show_last_update: e.show_last_update !== !1,
			filter_routes: q(e.filter_routes),
			exclude_routes: q(e.exclude_routes),
			destination_filter: q(e.destination_filter),
			exclude_destinations: q(e.exclude_destinations),
			filter_vehicle_types: q(e.filter_vehicle_types).map((e) => e.toLowerCase()),
			filter_providers: q(e.filter_providers),
			filter_platform: e.filter_platform || "",
			filter_track: e.filter_track || "",
			time_format: [
				"auto",
				"24h",
				"12h"
			].includes(e.time_format) ? e.time_format : "auto",
			icon: e.icon || "",
			show_footer: e.show_footer !== !1,
			tap_action: J(e.tap_action, "more-info"),
			hold_action: J(e.hold_action, "none"),
			double_tap_action: J(e.double_tap_action, "none")
		}, this.vehicleMap.preloadLeaflet();
	}
	getCardSize() {
		return (this._config.max_departures || 10) + 1;
	}
	connectedCallback() {
		super.connectedCallback(), this._startTick();
	}
	disconnectedCallback() {
		super.disconnectedCallback(), this._tickTimer &&= (clearInterval(this._tickTimer), null), this.vehicleMap.destroy();
	}
	_startTick() {
		this._tickTimer && clearInterval(this._tickTimer), this._tickTimer = setInterval(() => {
			this.requestUpdate();
		}, 1e4);
	}
	_getEntityIds() {
		return !this.hass || !this._config.entities?.length ? [] : this._config.entities.map((e) => typeof e == "string" ? e : e.entity).filter((e) => this.hass.states[e]);
	}
	_getAllDepartures() {
		if (!this.hass || !this._config.entities?.length) return [];
		let e = [];
		for (let t of this._getEntityIds()) {
			let n = this.hass.states[t];
			if (n?.attributes?.departures) {
				let r = this._config.entities.find((e) => (typeof e == "string" ? e : e.entity) === t);
				for (let i of n.attributes.departures) e.push({
					...i,
					_entityId: t,
					_entityConfig: r,
					_stopName: n.attributes.stop_name,
					_provider: n.attributes.provider
				});
			}
		}
		return e.sort((e, t) => new Date(e.estimated_time || e.theoretical_time) - new Date(t.estimated_time || t.theoretical_time));
	}
	_getDepartures() {
		if (!this.hass || !this._config.entities?.length) return [];
		let e = this._config, t = [], n = this._getEntityIds();
		if (e.view_mode === "tabs" && n.length > 1) {
			let e = n[this._activeTab], r = e ? this.hass.states[e] : null;
			if (r?.attributes?.departures) {
				let n = this._config.entities.find((t) => (typeof t == "string" ? t : t.entity) === e);
				t = r.attributes.departures.map((t) => ({
					...t,
					_entityId: e,
					_entityConfig: n,
					_stopName: r.attributes.stop_name,
					_provider: r.attributes.provider
				}));
			}
		} else t = this._getAllDepartures();
		let r = (e, t, n) => {
			let r = e._entityConfig && typeof e._entityConfig == "object" ? e._entityConfig : {};
			return t in r ? r[t] : n;
		}, i = (e, t) => Array.isArray(t) && t.length > 0 && t.some((t) => String(e || "").toLowerCase().includes(String(t).toLowerCase()));
		if (t = t.filter((t) => {
			if (r(t, "realtime_only", e.realtime_only) && !t.realtime) return !1;
			let n = r(t, "filter_routes", e.filter_routes);
			if (Array.isArray(n) && n.length && !n.some((e) => String(e).toUpperCase() === String(t.route || "").toUpperCase())) return !1;
			let a = r(t, "exclude_routes", e.exclude_routes);
			if (Array.isArray(a) && a.length && a.some((e) => String(e).toUpperCase() === String(t.route || "").toUpperCase())) return !1;
			let o = r(t, "destination_filter", e.destination_filter);
			if (Array.isArray(o) && o.length && !i(t.headsign, o) || i(t.headsign, r(t, "exclude_destinations", e.exclude_destinations))) return !1;
			let s = r(t, "filter_vehicle_types", e.filter_vehicle_types);
			if (Array.isArray(s) && s.length && !s.some((e) => String(e).toLowerCase() === String(t.vehicle_type || "").toLowerCase())) return !1;
			let c = r(t, "filter_providers", e.filter_providers);
			if (Array.isArray(c) && c.length && !c.includes(t._provider || t.provider || "")) return !1;
			let l = r(t, "filter_platform", e.filter_platform);
			if (l && String(t.platform || "") !== String(l)) return !1;
			let u = r(t, "filter_track", e.filter_track);
			return !(u && String(t.track || "") !== String(u) || r(t, "hide_terminus", e.hide_terminus) && t.headsign && t._stopName && t.headsign.toLowerCase() === t._stopName.toLowerCase() || r(t, "hide_cancelled", e.hide_cancelled) && t.cancelled);
		}), e.highlight_mode) {
			let e = {};
			for (let n of t) {
				let t = n.route + "|" + n.headsign;
				e[t] || (e[t] = []), e[t].push(n);
			}
			for (let t in e) e[t].sort((e, t) => new Date(e.estimated_time || e.theoretical_time) - new Date(t.estimated_time || t.theoretical_time)), e[t].forEach((e, t) => {
				t > 0 && (e._dimmed = !0);
			});
		}
		let a = {};
		return t = t.filter((t) => {
			let n = parseInt(r(t, "max_departures", e.max_departures)) || e.max_departures;
			return a[t._entityId] = (a[t._entityId] || 0) + 1, a[t._entityId] <= n;
		}), t.slice(0, e.max_departures);
	}
	_getAutoIcon() {
		if (!this.hass || !this._config.entities?.length) return Ue;
		let e = /* @__PURE__ */ new Set();
		for (let t of this._getEntityIds()) {
			let n = this.hass.states[t];
			n?.attributes?.provider && e.add(n.attributes.provider);
		}
		return e.size === 1 && e.has("plk_rail") ? We : Ge;
	}
	_getHeaderColor() {
		if (this._config.header_style === "theme") return "var(--primary-color, #005eb8)";
		if (this._config.header_style === "custom" && this._config.header_color) {
			let e = this._config.header_color;
			return /^(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\)|hsla?\([^)]+\)|linear-gradient\([^;{}]+\)|[a-zA-Z]{3,20})$/.test(e.trim()) ? e.trim() : "var(--primary-color, #005eb8)";
		}
		if (this._config.header_color) {
			let e = this._config.header_color;
			return /^(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\)|hsla?\([^)]+\)|linear-gradient\([^;{}]+\)|[a-zA-Z]{3,20})$/.test(e.trim()) ? e.trim() : "#005eb8";
		}
		let e = {
			ztm_gdansk: "#DA2128",
			zkm_gdynia: "#005eb8",
			mzk_wejherowo: "#478AC9",
			plk_rail: "#1a1a2e",
			...Me
		}, t = /* @__PURE__ */ new Set();
		if (this.hass && this._config.entities?.length) for (let e of this._getEntityIds()) {
			let n = this.hass.states[e];
			n?.attributes?.provider && t.add(n.attributes.provider);
		}
		let n = [...t];
		if (n.length === 1) return e[n[0]] || "#005eb8";
		if (n.length >= 2) {
			let t = [...new Set(n.map((t) => e[t] || "#005eb8"))];
			return t.length === 1 ? t[0] : `linear-gradient(135deg, ${t[0]} 0%, ${t[1]} 100%)`;
		}
		return "#005eb8";
	}
	_getTitle() {
		if (this._config.title) return this._config.title;
		if (!this.hass || !this._config.entities?.length) return "MZKZG Transport";
		let e = this._getEntityIds()[0], t = e ? this.hass.states[e] : null;
		return t?.attributes?.stop_name || t?.attributes?.friendly_name || "MZKZG Transport";
	}
	_getSubtitle() {
		if (!this.hass || !this._config.entities?.length) return "Wybierz encje";
		let e = /* @__PURE__ */ new Set();
		for (let t of this._getEntityIds()) {
			let n = this.hass.states[t];
			n?.attributes?.provider && e.add(n.attributes.provider);
		}
		return [...e].join(" + ") || "MZKZG";
	}
	_getClock() {
		let e = this.hass?.locale?.language || document.documentElement.lang || "pl-PL", t = this._config.time_format, n = t === "12h" || t === "auto" && this.hass?.locale?.time_format === "12";
		return new Intl.DateTimeFormat(e, {
			hour: "2-digit",
			minute: "2-digit",
			hour12: n
		}).format(/* @__PURE__ */ new Date());
	}
	_getLastUpdate() {
		if (!this.hass || !this._config.entities?.length) return "";
		let e = null;
		for (let t of this._getEntityIds()) {
			let n = this.hass.states[t]?.attributes?.last_update;
			n && (!e || n > e) && (e = n);
		}
		return e ? `Odświeżono: ${new Date(e).toLocaleTimeString("pl-PL", {
			hour: "2-digit",
			minute: "2-digit",
			second: "2-digit"
		})}` : "";
	}
	_resolveActionConfig(e) {
		let t = this._config || {};
		return e === "tap" ? J(t.tap_action, "more-info") : J(e === "hold" ? t.hold_action : t.double_tap_action, "none");
	}
	async _handleRowAction(e, t) {
		let n = this._resolveActionConfig(e), r = n.action || "none";
		if (r === "none") return;
		let i = t._entityId || this._config.entities[0];
		if (r === "more-info") {
			je(this, "hass-more-info", { entityId: i });
			return;
		}
		if (r === "navigate") {
			let e = n.navigation_path || "";
			if (!e) return;
			history.pushState(null, "", e), je(window, "location-changed", { replace: !1 });
			return;
		}
		if (r === "url") {
			let e = n.url_path || "";
			if (!e) return;
			window.open(e, "_blank", "noopener");
			return;
		}
		if (r === "toggle") {
			if (!this.hass || !i) return;
			await this.hass.callService("homeassistant", "toggle", { entity_id: i });
			return;
		}
		if (r === "perform-action" || r === "call-service") {
			if (!this.hass) return;
			let [e, t] = (n.perform_action || n.service || "").split(".");
			if (!e || !t) return;
			let r = { ...n.data || {} };
			n.target?.entity_id && (r.entity_id = n.target.entity_id), await this.hass.callService(e, t, r);
		}
	}
	_onRowClick(e, t) {
		if (W(t.vehicle_lat, t.vehicle_lng) !== null) {
			let e = W(t.vehicle_lat, t.vehicle_lng);
			this.vehicleMap.showVehicleMap(e[0], e[1], {
				route: t.route || "",
				code: t.vehicle_code || "",
				headsign: t.headsign || "",
				delay: Math.round((t.delay_seconds || 0) / 60),
				direction: parseFloat(t.vehicle_direction || t.direction) || null,
				provider: t._provider || t.provider || "",
				trip_id: t.trip_id,
				route_id_int: t.route_id_int,
				entityId: t._entityId,
				vehicleType: t.vehicle_type || "bus",
				lowFloor: t.floor_height && t.floor_height !== "Pojazd wysokopodłogowy",
				electric: t.drive_type === "elektryczny",
				articulated: t.articulated,
				historic: t.historic,
				vehicle_model: t.vehicle_model || "",
				vehicle_speed: t.vehicle_speed
			});
			return;
		}
		this._tapTimer && clearTimeout(this._tapTimer), this._tapTimer = setTimeout(() => this._handleRowAction("tap", t), 220);
	}
	_onRowDblClick(e, t) {
		this._tapTimer && clearTimeout(this._tapTimer), this._handleRowAction("double", t);
	}
	_onRowContext(e, t) {
		e.preventDefault(), this._handleRowAction("hold", t);
	}
	_renderTabs() {
		let e = this._config, t = this._getEntityIds();
		return e.view_mode !== "tabs" || t.length <= 1 ? N : A`
      <div class="tabs" role="tablist">
        ${t.map((e, t) => {
			let n = (this.hass?.states[e])?.attributes?.stop_name || e.replace("sensor.", "");
			return A`
            <span 
              class="tab ${t === this._activeTab ? "active" : ""}" 
              role="tab" 
              tabindex=${t === this._activeTab ? "0" : "-1"}
              aria-selected=${t === this._activeTab ? "true" : "false"}
              @click=${() => {
				this._activeTab = t;
			}}
            >${n}</span>
          `;
		})}
      </div>
    `;
	}
	_renderDeps() {
		let e = this._config;
		if (!e.entities?.length) return A`<div class="state-msg"><span class="icon">📍</span>${H("no_entities")}</div>`;
		if (!this.hass) {
			let t = e.min_departures !== void 0 && e.min_departures > 0 ? e.min_departures : Math.min(5, e.max_departures || 5);
			return Array.from({ length: t }).map(() => A`
        <div class="dep-row">
          <div class="skel" style="height:26px;width:40px;border-radius:6px"></div>
          <div class="skel" style="height:13px;flex:1"></div>
          <div class="skel" style="height:13px;width:60px"></div>
        </div>
      `);
		}
		let t = this._getDepartures();
		if (!t.length) {
			let e = this._getEntityIds().filter((e) => !this.hass.states[e]);
			if (e.length) {
				let t = e.map((e) => e.replace("sensor.", "")).join(", ");
				return A`<div class="state-msg"><span class="icon">⚠️</span>${H("missing_entities")}<br><small>${t}</small></div>`;
			}
			let t = this._getEntityIds().filter((e) => {
				let t = this.hass.states[e];
				return t && (t.state === "unavailable" || t.state === "unknown");
			});
			if (t.length) return A`<div class="state-msg"><span class="icon">⚠️</span>${t.some((e) => this.hass.states[e]?.attributes?.provider === "plk_rail") ? H("plk_rate_limit") : H("unavailable")}</div>`;
			let n = this._getAllDepartures();
			if (n.length) {
				let e = n[0], t = e.estimated_time ? G(e.estimated_time) : "";
				return A`<div class="state-msg"><span class="icon">🕐</span>${H("no_departures")}<br><small>${t ? (H("min") === "min" ? "Next" : "Następny") + ": " + e.route + " → " + e.headsign + " " + t : ""}</small></div>`;
			}
			return A`<div class="state-msg"><span class="icon">⏳</span>${H("no_departures")}</div>`;
		}
		let n = ["none"].indexOf(this._config.tap_action?.action || "more-info") === -1 || ["none"].indexOf(this._config.hold_action?.action || "none") === -1 || ["none"].indexOf(this._config.double_tap_action?.action || "none") === -1, r = (t) => {
			let r = Oe(t.estimated_time), i = t.realtime && r !== null && r <= 2, a = Math.round((t.delay_seconds || 0) / 60), o = e.show_delays && t.realtime && Math.abs(a) >= 1, s = t.cancelled === !0, c;
			if (s) c = A`<div class="time-main cancelled">${H("cancelled")}</div>`;
			else if (e.display_preset === "e_ink") c = A`<div class="time-main">${G(t.estimated_time || t.theoretical_time)}</div>`;
			else if (t.realtime) {
				let n = o ? A` <span class="delay-badge ${a > 0 ? "late" : "early"}">${a > 0 ? "+" : ""}${a}min</span>` : N, i = o ? A`<span class="time-struck">${G(t.theoretical_time || t.estimated_time)}</span> ${G(t.estimated_time)}` : G(t.estimated_time), s = r !== null && r <= 0 ? H("departing") : ke(r);
				c = e.show_countdown ? A`<div class="time-main">${i}</div><div class="time-sub"><span class="dot">●</span> ${s}${n}</div>` : A`<div class="time-main">${i}${n}</div>`;
			} else c = A`<div class="time-main">${G(t.theoretical_time || t.estimated_time)}</div>`;
			let l = N;
			e.show_platform && t._provider === "plk_rail" && (l = A`
          ${t.platform ? A`<span class="platform">peron ${t.platform}</span>` : N}
          ${t.track ? A`<span class="platform">${H("track")} ${t.track}</span>` : N}
        `);
			let u = [];
			e.show_accessibility && (e.show_bike && t.bike_allowed === !0 && u.push(A`<span title="Rower">${Z(Ke)}</span>`), e.show_wheelchair && t.wheelchair_accessible === !0 && u.push(A`<span title="Wózek">${Z(qe)}</span>`), e.show_ac && t.air_conditioning === !0 && u.push(A`<span title="Klimatyzacja">${Z(Je)}</span>`));
			let d = e.show_vehicle && t._provider !== "plk_rail" && t.vehicle_code && t.realtime ? A`<span class="platform">${t.vehicle_code}</span>` : N, f = e.show_platform && t.platform && t._provider !== "plk_rail" ? A`<span class="platform" title="Stanowisko/peron">${t.platform}</span>` : N, p = W(t.vehicle_lat, t.vehicle_lng) !== null, ee = u.length > 0 || f !== N || l !== N || p ? A`<span class="meta-row">
            <span class="icons">${u}</span>${l}${f}
            ${p ? A`<span class="map-pin" title=${H("show_on_map")}>${Z(Ye)}</span>` : N}
          </span>` : N, m = e.show_stop_name && e.entities.length > 1 && e.view_mode !== "tabs" && t._stopName, h = (t._stopName || "").replace(/\s*\(?(bus|tramwaj|tram|train|skm)\)?\s*/gi, " ").trim(), g = N;
			if (t.train_number && t._provider === "plk_rail") {
				let e = (t.carrier || "").replace(/^[„""'\s]+/, "").replace(/PKP\s*Szybka\s*Kolej\s*Miejska.*/i, "SKM").replace(/PKP\s*Intercity.*/i, "IC").replace(/POLREGIO.*/i, "Polregio").replace(/\s*sp\.?\s*z\s*o\.?\s*o\.?.*/i, "");
				g = A`<span class="stop-name">nr ${t.train_number} - ${e}</span>`;
			}
			let _ = n || p;
			return A`
        <div class="dep-row ${_ ? "interactive" : ""} ${i ? "imminent" : ""} ${t._dimmed ? "dimmed" : ""} ${s ? "cancelled" : ""}"
             tabindex=${_ ? "0" : "-1"}
             @click=${(e) => this._onRowClick(e, t)}
             @dblclick=${(e) => this._onRowDblClick(e, t)}
             @contextmenu=${(e) => this._onRowContext(e, t)}
             @keydown=${(e) => {
				(e.key === "Enter" || e.key === " ") && (e.preventDefault(), this._onRowClick(e, t));
			}}>
          <span class="badge" style="background:${K(t.route, t._provider || t.provider, t.route_color)}">${t.route}</span>
          <span class="headsign">
            <span class="head-main"><span class="headsign-text">${t.headsign}</span>${d}</span>
            ${ee}
            ${g === N ? m ? A`<span class="stop-name">${h}</span>` : N : g}
          </span>
          <div class="time-col">${c}</div>
        </div>
      `;
		}, i = [];
		if (e.group_by_provider) {
			let e = {};
			t.forEach((t) => {
				let n = t._provider || "Inne";
				e[n] || (e[n] = []), e[n].push(t);
			});
			for (let t in e) {
				let n;
				n = t === "ztm_gdansk" ? "ZTM Gdańsk" : t === "zkm_gdynia" ? "ZKM Gdynia" : t === "mzk_wejherowo" ? "MZK Wejherowo" : t === "plk_rail" ? "Pociągi (SKM/IC/PR)" : t.charAt(0).toUpperCase() + t.slice(1), i.push(A`<div class="provider-header">${n}</div>`), e[t].forEach((e) => i.push(r(e)));
			}
		} else t.forEach((e) => i.push(r(e)));
		let a = this._config.min_departures === void 0 ? 0 : parseInt(this._config.min_departures), o = t.length;
		if (o > 0 && o < a) {
			let e = a - o;
			for (let t = 0; t < e; t++) i.push(A`<div class="dep-row" style="visibility:hidden">&nbsp;</div>`);
		}
		return i;
	}
	render() {
		if (!this._config) return N;
		let e = this._config;
		return A`
      <ha-card class="${e.display_preset === "e_ink" ? "e-ink" : e.display_preset === "compact" ? "compact" : e.display_preset === "minimal" ? "minimal" : ""}" data-theme="${e.theme_mode}" data-header="${e.header_style}">
        ${e.show_header ? A`
          <div class="header" style="background:${this._getHeaderColor()}">
            <span class="header-icon">${e.icon ? A`<ha-icon icon="${e.icon}" style="color:var(--mzkzg-header-text, #fff);--mdc-icon-size:20px"></ha-icon>` : this._getAutoIcon()}</span>
            <div class="header-body">
              <div class="header-title">${this._getTitle()}</div>
              <div class="header-sub">${this._getSubtitle()}</div>
            </div>
            ${e.show_clock ? A`<div class="header-clock">${this._getClock()}</div>` : N}
          </div>
        ` : N}
        ${this._renderTabs()}
        <div class="dep-list" aria-live="polite" aria-atomic="true">
          ${this._renderDeps()}
        </div>
        ${e.show_footer && e.show_last_update ? A`<div class="footer">${this._getLastUpdate()}</div>` : N}
      </ha-card>
    `;
	}
};
customElements.get("mzkzg-transport-card") || customElements.define("mzkzg-transport-card", Xe), customElements.get("polish-transport-card") || customElements.define("polish-transport-card", class extends Xe {}), window.customCards = window.customCards || [], window.customCards.push({
	type: "polish-transport-card",
	name: "Polish Transport Card",
	description: "Tablica odjazdów polskiej komunikacji miejskiej (dane z integracji mzkzg_transport)",
	preview: !0,
	documentationURL: "https://github.com/toczke/polish-public-transport-card"
}), console.info(`%c MZKZG-TRANSPORT %c v${De} `, "background:#005eb8;color:#fff;padding:2px 6px;border-radius:4px 0 0 4px;font-weight:bold", "background:#1f2937;color:#fff;padding:2px 6px;border-radius:0 4px 4px 0");
//#endregion
