// ===== 定数 =====
const GAME_TIME = 10; // ゲームの制限時間（秒）
const BEST_SCORE_KEY = 'clickGame_bestScore'; // localStorage のキー名

// ===== ゲームの状態を管理する変数 =====
let score = 0;        // 現在のスコア（クリック数）
let timeLeft = GAME_TIME; // 残り時間
let timerId = null;   // setInterval で返ってくるID（停止に使う）
let isPlaying = false; // ゲーム中かどうか

// ===== HTML の要素を取得 =====
const timerEl      = document.getElementById('timer');
const scoreEl      = document.getElementById('score');
const bestScoreEl  = document.getElementById('best-score');
const mainBtn      = document.getElementById('main-btn');
const resultMsg    = document.getElementById('result-message');

// ===== 初期化処理：ページ読み込み時に最高スコアを表示 =====
function init() {
  const savedBest = localStorage.getItem(BEST_SCORE_KEY);
  // localStorage には文字列で保存されるので数値に変換する
  bestScoreEl.textContent = savedBest ? parseInt(savedBest, 10) : 0;
}

// ===== ボタンが押されたときの処理 =====
function handleButtonClick() {
  if (!isPlaying) {
    // ゲームが始まっていない → スタートする
    startGame();
  } else {
    // ゲーム中 → クリックをカウント
    addClick();
  }
}

// ===== ゲームを開始する =====
function startGame() {
  // 状態をリセット
  score = 0;
  timeLeft = GAME_TIME;
  isPlaying = true;

  // 画面を更新
  scoreEl.textContent = 0;
  timerEl.textContent = GAME_TIME;
  timerEl.classList.remove('danger');
  resultMsg.textContent = '';
  resultMsg.classList.remove('show');

  // ボタンをクリック用のスタイルに変える
  mainBtn.textContent = 'クリック！';
  mainBtn.classList.add('playing');

  // 1秒ごとにカウントダウンする
  timerId = setInterval(tick, 1000);
}

// ===== 1秒ごとに呼ばれるカウントダウン処理 =====
function tick() {
  timeLeft--;
  timerEl.textContent = timeLeft;

  // 残り3秒以下で警告表示
  if (timeLeft <= 3) {
    timerEl.classList.add('danger');
  }

  // 残り時間がゼロになったらゲーム終了
  if (timeLeft <= 0) {
    endGame();
  }
}

// ===== クリックをカウントする =====
function addClick() {
  score++;
  scoreEl.textContent = score;

  // スコアがポンと拡大するアニメーション
  popAnimation(scoreEl);
}

// ===== ゲームを終了する =====
function endGame() {
  isPlaying = false;

  // タイマーを止める
  clearInterval(timerId);
  timerId = null;

  // ボタンを無効化（ゲーム中に余分なクリックを防ぐ）
  mainBtn.disabled = true;
  mainBtn.classList.remove('playing');
  mainBtn.textContent = '終了！';

  // 最高スコアを確認・更新
  const currentBest = parseInt(localStorage.getItem(BEST_SCORE_KEY) || '0', 10);
  const isNewRecord = score > currentBest;

  if (isNewRecord) {
    localStorage.setItem(BEST_SCORE_KEY, score);
    bestScoreEl.textContent = score;
    popAnimation(bestScoreEl);
  }

  // 結果メッセージを表示
  showResult(isNewRecord);

  // 少し待ってからリセット（もう一度遊べるようにする）
  setTimeout(resetGame, 2500);
}

// ===== 結果メッセージを表示する =====
function showResult(isNewRecord) {
  if (isNewRecord) {
    resultMsg.textContent = `新記録！ ${score} クリック！`;
  } else if (score >= 50) {
    resultMsg.textContent = `すごい！ ${score} クリック！`;
  } else if (score >= 30) {
    resultMsg.textContent = `いい感じ！ ${score} クリック！`;
  } else {
    resultMsg.textContent = `${score} クリック！ もう一度挑戦！`;
  }

  // CSSのトランジションで滑らかに表示
  // setTimeout(0) を使うことで、テキスト設定後にクラスが適用される
  setTimeout(() => resultMsg.classList.add('show'), 0);
}

// ===== ゲームをリセットしてスタートボタンに戻す =====
function resetGame() {
  mainBtn.disabled = false;
  mainBtn.textContent = 'スタート';
  timerEl.textContent = GAME_TIME;
  timerEl.classList.remove('danger');
}

// ===== 数値がポンと拡大するアニメーション =====
function popAnimation(element) {
  // すでにアニメーション中なら一旦クラスを外してリセット
  element.classList.remove('pop');

  // requestAnimationFrame でブラウザの描画タイミングに合わせてクラスを追加
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      element.classList.add('pop');
      // アニメーションが終わったらクラスを外す（80ms = CSS の transition 時間と一致）
      setTimeout(() => element.classList.remove('pop'), 80);
    });
  });
}

// ===== クリック時のリップルエフェクト =====
mainBtn.addEventListener('click', function (e) {
  if (!isPlaying) return; // スタート前はリップルなし

  const btn = this;
  const rect = btn.getBoundingClientRect();

  // クリックした位置を計算（ボタン内の相対座標）
  const x = e.clientX - rect.left - 30; // 30 = ripple の半径
  const y = e.clientY - rect.top - 30;

  // リップル要素を作成してボタンに追加
  const ripple = document.createElement('span');
  ripple.className = 'ripple';
  ripple.style.left = x + 'px';
  ripple.style.top  = y + 'px';
  btn.appendChild(ripple);

  // アニメーションが終わったら要素を削除（メモリの無駄を防ぐ）
  ripple.addEventListener('animationend', () => ripple.remove());
});

// ===== ページ読み込み時に初期化を実行 =====
init();
