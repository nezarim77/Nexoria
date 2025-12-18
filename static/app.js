document.addEventListener('DOMContentLoaded', ()=>{
  const pull10 = document.getElementById('pull10')
  const resultArea = document.getElementById('resultArea')
  const buyBtns = document.querySelectorAll('.buyBox')
  const shopResult = document.getElementById('shopResult')
  const resetBtn = document.getElementById('resetBtn')
  const resetLobby = document.getElementById('resetLobby')

    /* =========================
     BOX IMAGE BY RARITY
  ========================= */
  function getBoxImageByRarity(rarity){
    const map = {
      'A':  '/static/public/box/a-box.png',
      'B':  '/static/public/box/b-box.png',
      'S':  '/static/public/box/s-box.png',
      'SS': '/static/public/box/ss-box.png'
    }

    return map[rarity] || '/static/public/box/a-box.png'
  }


  const COIN_IMG = 'https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/cd9b85bb-f709-41fb-8666-da35e37527e0/ddj39zb-3b4362e1-1f54-4aae-95ba-50fb7f6127d5.png?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOjdlMGQxODg5ODIyNjQzNzNhNWYwZDQxNWVhMGQyNmUwIiwiaXNzIjoidXJuOmFwcDo3ZTBkMTg4OTgyMjY0MzczYTVmMGQ0MTVlYTBkMjZlMCIsIm9iaiI6W1t7InBhdGgiOiIvZi9jZDliODViYi1mNzA5LTQxZmItODY2Ni1kYTM1ZTM3NTI3ZTAvZGRqMzl6Yi0zYjQzNjJlMS0xZjU0LTRhYWUtOTViYS01MGZiN2Y2MTI3ZDUucG5nIn1dXSwiYXVkIjpbInVybjpzZXJ2aWNlOmZpbGUuZG93bmxvYWQiXX0.sBkYEkdbznOgmxGjN0Tkt1EebgRfRIJlHCUoNp_gvb0'
  const TICKET_IMG = 'https://gpng.net/wp-content/uploads/2020/10/ticket-png-template-free-png-images-2-pngandscrap.png'

  function updateCoins(n){
    const el = document.getElementById('coins')
    if(el) el.innerHTML = `${n} <img class="currency-icon coin" src="${COIN_IMG}" alt="coin">`
  }

  function updateTickets(n){
    const el = document.getElementById('tickets')
    if(el) el.innerHTML = `${n} <img class="currency-icon ticket" src="${TICKET_IMG}" alt="ticket">`
  }

  function updateBuyButtons(){
    // ❗ TIDAK disable tombol shop lagi
    // fungsi dibiarkan agar tidak merusak fitur lama
  }

  /* =========================
     MODAL HELPER
  ========================= */
  function showModal({title, text, actions=[]}){
    const old = document.querySelector('.modal-overlay')
    if(old) old.remove()

    const overlay = document.createElement('div')
    overlay.className = 'modal-overlay'
    overlay.innerHTML = `
      <div class="modal">
        <h3>${title}</h3>
        <p>${text}</p>
        <div class="modal-actions"></div>
      </div>
    `
    const actionWrap = overlay.querySelector('.modal-actions')

    actions.forEach(a=>{
      const btn = document.createElement('button')
      btn.textContent = a.label
      btn.className = a.class || ''
      btn.onclick = ()=>{
        overlay.remove()
        if(a.onClick) a.onClick()
      }
      actionWrap.appendChild(btn)
    })

    overlay.addEventListener('click', e=>{
      if(e.target === overlay) overlay.remove()
    })

    document.body.appendChild(overlay)
  }

  /* =========================
     RESET (CUSTOM MODAL)
  ========================= */
  function confirmReset(){
    showModal({
      title: 'Reset Progress?',
      text: 'Semua kartu, koin, dan tiket akan dihapus.',
      actions: [
        { label:'Batal', class:'btn-secondary' },
        { label:'Reset', class:'btn-danger', onClick: async ()=>{
            const res = await fetch('/reset',{method:'POST'})
            let j = {ok:false, error:'No response'}
            const ct = res.headers.get('content-type') || ''
            if(ct.includes('application/json')){
              j = await res.json().catch(()=>({ok:false,error:'Invalid JSON'}))
            } else {
              const text = await res.text().catch(()=>null)
              j = {ok:false, error: text || 'Invalid response from server'}
            }
            console.log('reset response', res.status, j)
            if(res.ok && j.ok) location.reload()
            else showModal({title:'Reset gagal', text: j.error || 'Terjadi kesalahan saat mereset.', actions:[{label:'OK'}]})
          }
        }
      ]
    })
  }

  if(resetBtn) resetBtn.addEventListener('click', confirmReset)
  if(resetLobby) resetLobby.addEventListener('click', confirmReset)

  /* =========================
     GACHA PULL (ASLI + UTUH)
  ========================= */
  if(pull10) pull10.addEventListener('click', ()=>doPull(10))

  async function doPull(count){
    if(pull10) pull10.disabled = true

    const gachaHero = document.querySelector('.gacha-hero')
    if(gachaHero) gachaHero.style.display = 'none'

    resultArea.classList.remove('single')
    resultArea.innerHTML = 'Pulling...'

    const res = await fetch('/pull',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({count})
    })

    const j = await res.json().catch(()=>({ok:false,error:'server'}))

    if(!j.ok){
      if(j.error && j.error.toLowerCase().includes('not enough coin')){
  resultArea.innerHTML = `
    <div class="no-coins-overlay">
      <div class="no-coins">
        <img src="/static/public/assets/aqua-cry.png" alt="Koin habis">
        <div class="no-coins-text">Yah, koinmu habis</div>
      </div>
    </div>
  `

  // ✅ TAMBAHKAN INI
  const overlay = document.querySelector('.no-coins-overlay')
  if(overlay){
    overlay.addEventListener('click', ()=>{
      overlay.remove()
    })
  }

  if(pull10) pull10.disabled = false
  return
}

      resultArea.innerHTML = '<div class="card-back">Error</div>'
      pull10.disabled = false
      return
    }

    updateCoins(j.coins)
    if(typeof j.tickets !== 'undefined') updateTickets(j.tickets)

    resultArea.innerHTML = ''
    if(count === 1) resultArea.classList.add('single')

    j.results.forEach((card, i)=>{
      const wrapper = document.createElement('div')
      wrapper.className = 'card flip-card rarity-'+card.rarity.toLowerCase()

      const inner = document.createElement('div')
      inner.className = 'card-inner'

      const front = document.createElement('div')
      front.className = 'card-front rarity-'+card.rarity.toLowerCase()

      if(card.image){
        const img = document.createElement('img')
        img.className = 'card-image'
        img.src = card.image.startsWith('http')
  ? card.image
  : '/static/' + card.image;

        front.appendChild(img)
      }

      const overlay = document.createElement('div')
      overlay.className = 'card-overlay'
      overlay.innerHTML = `
        <div class="card-name">${card.name}</div>
        <div class="card-rarity">${card.rarity}</div>
        <div class="card-desc">${card.desc}</div>
      `

      if(card.duplicate){
        const badge = document.createElement('div')
        badge.className = 'duplicate-badge'
        badge.textContent = `Duplicate: +${card.tickets_awarded} tickets`
        overlay.appendChild(badge)
      }

      front.appendChild(overlay)

      const back = document.createElement('div')
      back.className = 'card-back card-back-result'
      back.innerHTML = `<div class="back-logo">NEXORIA</div><div class="ribbon">${card.rarity}</div>`

      inner.append(back, front)
      wrapper.appendChild(inner)
      resultArea.appendChild(wrapper)

      setTimeout(()=>wrapper.classList.add('flipped'), i*200+600)
    })

    setTimeout(()=>{ pull10.disabled = false }, j.results.length*200+1200)
  }

  /* =========================
     SHOP (BUTTON TETAP AKTIF)
  ========================= */
  buyBtns.forEach(btn=>{
    btn.addEventListener('click', async ()=>{
      const rarity = btn.dataset.rarity
      shopResult.innerHTML = ''

      const res = await fetch('/buy',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({rarity})
      })

      const j = await res.json()

      if(!j.ok){
  if(j.error){
    if(j.error.toLowerCase().includes('ticket')){
      showModal({
        title:'Tiket Tidak Cukup',
        text:'Dapatkan tiket dari duplicate kartu gacha.',
        actions:[{label:'OK', class:'btn-secondary'}]
      })
    }
    else if(j.error.toLowerCase().includes('no unowned')){
      showModal({
        title:'Box Kosong',
        text:'Semua kartu di box ini sudah kamu miliki.',
        actions:[{label:'OK', class:'btn-secondary'}]
      })
    }
    else{
      showModal({
        title:'Gagal',
        text: j.error,
        actions:[{label:'OK'}]
      })
    }
  }
  shopResult.innerHTML = ''
  return
}


        updateTickets(j.tickets)

        const boxImg = getBoxImageByRarity(j.card.rarity)

        // show overlay with centered box animation
        showShopOverlay(`
          <div class="box-opening rarity-${j.card.rarity.toLowerCase()}">
            <img src="${boxImg}">
          </div>
        `)

        // give the box animation a bit more time, and mark it opened
        const ov = document.querySelector('.shop-overlay')
        const boxCont = ov && ov.querySelector('.shop-box-container')
        if(boxCont) boxCont.classList.add('opened')

        setTimeout(()=>{
          if(!j || !j.card){
            console.warn('shop: no card in response', j)
            showModal({title:'Gagal', text:'Tidak ada kartu ditemukan dari server.', actions:[{label:'OK'}]})
            removeOverlayAndCentered()
            return
          }
          showShopCardCentered(j.card)
        },1600)
    })
  })

  function showShopCard(card){
    shopResult.innerHTML = ''

    const wrapper = document.createElement('div')
    wrapper.className = 'card flip-card rarity-'+card.rarity.toLowerCase()

    const inner = document.createElement('div')
    inner.className = 'card-inner'

    const front = document.createElement('div')
    front.className = 'card-front rarity-'+card.rarity.toLowerCase()

    if(card.image){
      const img = document.createElement('img')
      img.className = 'card-image'
      img.src = card.image.startsWith('http')
  ? card.image
  : '/static/' + card.image;

      front.appendChild(img)
    }

    const overlay = document.createElement('div')
    overlay.className = 'card-overlay'
    overlay.innerHTML = `
      <div class="card-name">${card.name}</div>
      <div class="card-rarity">${card.rarity}</div>
      <div class="card-desc">${card.desc}</div>
    `
    front.appendChild(overlay)

    const back = document.createElement('div')
    back.className = 'card-back card-back-result'
    back.innerHTML = `<div class="back-logo">NEXORIA</div><div class="ribbon">${card.rarity}</div>`

    inner.append(back, front)
    wrapper.appendChild(inner)
    shopResult.appendChild(wrapper)

    setTimeout(()=>wrapper.classList.add('flipped'),600)
  }

  function removeOverlayAndCentered(){
    const centered = document.querySelector('.shop-result-center')
    if(centered) centered.remove()
    const ov = document.querySelector('.shop-overlay')
    if(ov) ov.remove()
  }

function showShopOverlay(boxHtml){
  // remove existing overlay if present
  const old = document.querySelector('.shop-overlay')
  if(old) old.remove()

  const overlay = document.createElement('div')
  overlay.className = 'shop-overlay'
  overlay.innerHTML = `
    <div class="shop-overlay-content">
      <button class="shop-overlay-close">✕</button>
      <div class="shop-box-container">
        ${boxHtml}
      </div>
      <div class="shop-overlay-cards" id="shopOverlayResult"></div>
    </div>
  `

  // close should remove centered result as well
  overlay.querySelector('.shop-overlay-close').onclick = ()=> removeOverlayAndCentered()
  overlay.addEventListener('click', e=>{
    if(e.target === overlay) removeOverlayAndCentered()
  })

  document.body.appendChild(overlay)
}

  function showShopCardCentered(card){
    console.log('showShopCardCentered', card)
    // ensure overlay exists
    let overlay = document.querySelector('.shop-overlay')
    if(!overlay) showShopOverlay('')
    overlay = document.querySelector('.shop-overlay')
    if(!overlay) return

    // remove any previous centered result
    const prev = document.querySelector('.shop-result-center')
    if(prev) prev.remove()

    const center = document.createElement('div')
    center.className = 'shop-result-center'

    const wrapper = document.createElement('div')
    wrapper.className = 'card flip-card rarity-'+card.rarity.toLowerCase()

    const inner = document.createElement('div')
    inner.className = 'card-inner'

    const front = document.createElement('div')
    front.className = 'card-front rarity-'+card.rarity.toLowerCase()

    if(card.image){
      const img = document.createElement('img')
      img.className = 'card-image'
      img.src = card.image.startsWith('http') ? card.image : '/static/' + card.image
      front.appendChild(img)
    }

    

    const overlayInfo = document.createElement('div')
    overlayInfo.className = 'card-overlay'
    overlayInfo.innerHTML = `
      <div class="card-name">${card.name}</div>
      <div class="card-rarity">${card.rarity}</div>
      <div class="card-desc">${card.desc}</div>
    `
    front.appendChild(overlayInfo)

    const back = document.createElement('div')
    back.className = 'card-back card-back-result'
    back.innerHTML = `<div class="back-logo">NEXORIA</div><div class="ribbon">${card.rarity}</div>`

    inner.append(back, front)
    wrapper.appendChild(inner)

    // hide the box container so it doesn't occlude the centered card
    const boxCont = overlay.querySelector('.shop-box-container')
    if(boxCont) boxCont.classList.add('hidden')

    // close button for centered result
    const close = document.createElement('button')
    close.className = 'shop-result-center-close'
    close.textContent = '✕'
    close.onclick = removeOverlayAndCentered

    center.appendChild(close)
    center.appendChild(wrapper)

    // append to body (fixed positioning) so it's guaranteed above overlay content
    document.body.appendChild(center)

    setTimeout(()=>wrapper.classList.add('flipped'), 100)
    // focus the close so keyboard users can close quickly
    close.focus()
  }
})
