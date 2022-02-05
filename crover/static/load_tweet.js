Vue.component('emotion-tweets', {
    template: '#emotion-tweets',
    data:function(){
        return {
            tweets: {
                positive: {
                    tweet: posi_tweet_init['tweet'],
                    load_continue: posi_tweet_init['load_continue'],
                },
                neutral: {
                    tweet: neut_tweet_init['tweet'],
                    load_continue: neut_tweet_init['load_continue'],
                },
                negative: {
                    tweet: nega_tweet_init['tweet'],
                    load_continue: nega_tweet_init['load_continue'],
                },
            },
        }
    },
    methods: {
        load: function(emotion) {
          console.log(emotion);
          let self = this;
          $.get("/ajax_load_tweet/" + emotion + "/" + this.tweets[emotion]['tweet'].length,
            function(loaded_tweet) {
                self.tweets[emotion]['tweet'] = self.tweets[emotion]['tweet'].concat(loaded_tweet.tweet);
                self.tweets[emotion]['load_continue'] = loaded_tweet.load_continue
            }
          );
        }
    }
});

// 他のファイルに以下記載すると他のjavascriptの動作に影響する
new Vue({
    el:'#app',
    //delimiters:['[[',']]']  //なぜかdelimiters変わらない
});
